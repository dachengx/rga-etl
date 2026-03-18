import os
import time
import logging

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)


# -------------------------
# Config
# -------------------------
HTTP_PORT = 8080
MQTT_BROKER = os.getenv("MQTT_BROKER", "169.254.11.119")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = "brx/control"

PUBLISH_TOPIC = f"{MQTT_TOPIC_PREFIX}/generic"
SUBSCRIBE_TOPIC = f"{MQTT_TOPIC_PREFIX}/result"


# -------------------------
# MQTT callbacks
# -------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(SUBSCRIBE_TOPIC)
        logging.info(f"Subscribed to {SUBSCRIBE_TOPIC}")
    else:
        logging.error(f"MQTT connect failed with rc={rc}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8", errors="replace")
        logging.info(f"Received on {msg.topic}: {payload}")
    except Exception as e:
        logging.error(f"Failed to process message from {msg.topic}: {e}")


def publish(topic, value):
    try:
        mqtt_client.publish(topic, str(value))
    except Exception as e:
        logging.error(f"Failed to publish to {topic}: {e}")


# -------------------------
# MQTT setup
# -------------------------
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

command = {
    "main": "ID?\r",
    "length": 128,
    "noresult": 0,
    # commented out because RGA can not change timeout
    # "timeout": 10000,  # in milliseconds
}

publish(PUBLISH_TOPIC, 1)
for key, value in command.items():
    topic = f"{MQTT_TOPIC_PREFIX}/{key}"
    publish(topic, value)


# -------------------------
# Keep program alive so subscriber can listen
# -------------------------
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("Stopping MQTT client...")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
