import os
import logging

import paho.mqtt.client as mqtt


def publish(topic, value):
    try:
        mqtt_client.publish(topic, str(value))
    except Exception as e:
        logging.error(f"Failed to publish to {topic}: {e}")


# -------------------------
# Config
# -------------------------
HTTP_PORT = 8080
MQTT_BROKER = os.getenv("MQTT_BROKER", "169.254.11.119")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = "brx/control"

# -------------------------
# MQTT setup
# -------------------------
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()
logging.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")

command = {
    "main": "ID?\r",
    "length": 128,
    "noresult": 0,
    # commented out because RGA can not change timeout
    # "timeout": 10000,  # in milliseconds
}

publish(f"{MQTT_TOPIC_PREFIX}/generic", 1)
for key, value in command.items():
    topic = f"{MQTT_TOPIC_PREFIX}/{key}"
    publish(topic, value)
