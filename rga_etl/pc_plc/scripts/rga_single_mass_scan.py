import os
import time
import logging

from rga_etl.pc_plc.mqtt_runner import MQTTCommandRunner

logging.basicConfig(level=logging.INFO)


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
