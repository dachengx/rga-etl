import time
import queue
import logging
import threading

import paho.mqtt.client as mqtt

from rga_etl.pc_plc.post_command import process as post_process


class MQTTCommandRunner:
    def __init__(
        self,
        broker,
        port,
        topic_prefix,
        publish_topic_suffix="generic",
        result_topic_suffix="result",
        sleep_between_commands=0.0,
    ):
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix
        self.publish_topic = f"{topic_prefix}/{publish_topic_suffix}"
        self.result_topic = f"{topic_prefix}/{result_topic_suffix}"
        self.sleep_between_commands = sleep_between_commands

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.command_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.current_wait_event = None
        self.current_result = None
        self.current_command = None

        self.worker_thread = threading.Thread(
            target=self._command_worker,
            daemon=True,
        )

    # -------------------------
    # MQTT callbacks
    # -------------------------
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            client.subscribe(self.result_topic)
            logging.info(f"Subscribed to {self.result_topic}")
        else:
            logging.error(f"MQTT connect failed with rc={rc}")

    def on_message(self, client, userdata, msg):
        if self.current_command is None:
            logging.warning(f"Unexpected message on {msg.topic} — no command in progress, ignoring")
            return
        try:
            result = post_process(self.current_command, msg.payload)
            logging.info(f"Received on {msg.topic}: {result}")

            self.current_result = result

            if self.current_wait_event is not None:
                self.current_wait_event.set()

        except Exception as e:
            logging.error(f"Failed to process message from {msg.topic}: {e}")

    # -------------------------
    # Basic MQTT operations
    # -------------------------
    def is_busy(self):
        return not self.command_queue.empty() or self.current_command is not None

    def connect(self):
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        self.worker_thread.start()

    def disconnect(self):
        self.stop_event.set()
        self.command_queue.put(None)  # unblock worker if needed
        self.worker_thread.join(timeout=2)

        self.client.loop_stop()
        self.client.disconnect()
        logging.info("MQTT client stopped")

    def publish(self, topic, value):
        try:
            self.client.publish(topic, str(value))
            logging.info(f"Published to {topic}: {value}")
        except Exception as e:
            logging.error(f"Failed to publish to {topic}: {e}")

    # -------------------------
    # Public API
    # -------------------------
    def run_commands(self, commands):
        results = []
        for command in commands:
            self.command_queue.put(command)
            self.command_queue.join()
            result = self.current_result
            if isinstance(result, Exception):
                raise result
            results.append(result if command.get("noresult", 0) == 0 else None)
        return results

    # -------------------------
    # Internal worker
    # -------------------------
    def _command_worker(self):
        while not self.stop_event.is_set():
            command = self.command_queue.get()
            if command is None:
                break

            self.current_command = command
            self.current_result = None

            logging.info(f"Sending command: {command}")

            # trigger/send command group
            for key, value in command.items():
                if key == "timeout":
                    continue
                topic = f"{self.topic_prefix}/{key}"
                self.publish(topic, value)
            # must inform the subscriber to start executing the command after all parameters are set
            self.publish(self.publish_topic, 1)

            # wait only if result is expected
            if command.get("noresult", 0) == 0:
                self.current_wait_event = threading.Event()

                logging.info("Waiting for result...")
                ok = self.current_wait_event.wait(timeout=command["timeout"])

                if ok:
                    logging.info(f"Command finished with result: {self.current_result}")
                else:
                    self.current_result = TimeoutError(
                        f"Timeout waiting for result for command: {command}"
                    )

                self.current_wait_event = None
            else:
                logging.info("Command does not require result, continuing immediately")

            self.command_queue.task_done()
            self.current_command = None

            time.sleep(self.sleep_between_commands)  # small delay between commands
