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
        sleep_between_commands=0.0,
    ):
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix
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
        else:
            logging.error(f"MQTT connect failed with rc={rc}")

    def on_message(self, client, userdata, msg):
        if self.current_command is None:
            logging.warning(f"Unexpected message on {msg.topic} — no command in progress, ignoring")
            return
        try:
            response = post_process(self.current_command, msg.payload)
            logging.info(f"Received on {msg.topic}: {response}")
            self.current_result = response
        except Exception as e:
            logging.error(f"Failed to process message from {msg.topic}: {e}")
            self.current_result = e
        finally:
            if self.current_wait_event is not None:
                self.current_wait_event.set()

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

    def subscribe(self, topic):
        try:
            self.client.subscribe(topic)
            logging.info(f"Subscribed to {topic}")
        except Exception as e:
            logging.error(f"Failed to subscribe to {topic}: {e}")

    # -------------------------
    # Public API
    # -------------------------
    def run_commands(self, commands):
        responses = []
        for command in commands:
            self.command_queue.put(command)
            self.command_queue.join()
            response = self.current_result
            if isinstance(response, Exception):
                raise response
            responses.append(response if command.get("noresponse", 0) == 0 else None)
        return responses

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

            publish_topic = f"{self.topic_prefix}/{command['publish']}"
            subscribe_topic = f"{self.topic_prefix}/{command['subscribe']}"

            # Subscribe and arm the wait event BEFORE publishing the trigger so that
            # a fast PLC response (e.g. serial data already buffered) cannot arrive
            # between the trigger publish and the event creation and be silently lost.
            if command.get("noresponse", 0) == 0:
                self.subscribe(subscribe_topic)
                self.current_wait_event = threading.Event()

            # publish parameters, then trigger execution.
            # Keys used only for Python-side routing are excluded from MQTT.
            # Commands marked with _skip_params only send the trigger — the PLC
            # retains parameter values from the previous identical sub-command.
            _ROUTING_KEYS = {"timeout", "publish", "subscribe"}
            if not command.get("_skip_params", False):
                for key, value in command.items():
                    if key in _ROUTING_KEYS or key.startswith("_"):
                        continue
                    topic = f"{self.topic_prefix}/{key}"
                    self.publish(topic, value)

            # must inform the subscriber to start executing the command after all parameters are set
            self.publish(publish_topic, 1)

            if command.get("noresponse", 0) == 0:
                logging.info("Waiting for response...")
                ok = self.current_wait_event.wait(timeout=command["timeout"])

                if ok:
                    logging.info(f"Command finished with response: {self.current_result}")
                else:
                    self.current_result = TimeoutError(
                        f"Timeout waiting for response for command: {command}"
                    )

                self.current_wait_event = None
            else:
                logging.info("Command does not require response, continuing immediately")

            self.command_queue.task_done()
            self.current_command = None

            time.sleep(self.sleep_between_commands)  # small delay between commands
