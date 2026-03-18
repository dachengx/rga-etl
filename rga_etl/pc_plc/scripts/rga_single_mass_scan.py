import os
import time
import queue
import logging
import threading

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)


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
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
            logging.info(f"Received on {msg.topic}: {payload}")

            self.current_result = payload

            if self.current_wait_event is not None:
                self.current_wait_event.set()

        except Exception as e:
            logging.error(f"Failed to process message from {msg.topic}: {e}")

    # -------------------------
    # Basic MQTT operations
    # -------------------------
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
    def submit_command(self, command):
        self.command_queue.put(command)

    def submit_commands(self, commands):
        for command in commands:
            self.submit_command(command)

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
                    logging.warning(f"Timeout waiting for result for command: {command}")

                self.current_wait_event = None
            else:
                logging.info("Command does not require result, continuing immediately")

            self.command_queue.task_done()

            time.sleep(self.sleep_between_commands)  # small delay between commands


# -------------------------
# Config
# -------------------------
MQTT_BROKER = os.getenv("MQTT_BROKER", "169.254.11.119")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = "brx/control"


# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    runner = MQTTCommandRunner(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        topic_prefix=MQTT_TOPIC_PREFIX,
    )

    runner.connect()

    commands = [
        {
            "main": "ID?\r",
            "length": 128,
            "noresult": 0,
            "timeout": 1.0,
        },
        {
            "main": "IN0\r",
            "length": 128,
            "noresult": 0,
            "timeout": 1.0,
        },
        {
            "main": "FL1.0\r",
            "length": 128,
            "noresult": 0,
            "timeout": 10.0,
        },
        {
            "main": "MR28\r",
            "length": 4,
            "noresult": 0,
            "timeout": 1.0,
        },
        {
            "main": "MR0\r",
            "length": 128,
            "noresult": 1,
            "timeout": 1.0,
        },
        {
            "main": "FL0.0\r",
            "length": 128,
            "noresult": 0,
            "timeout": 10.0,
        },
    ]

    runner.submit_commands(commands)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        runner.disconnect()
