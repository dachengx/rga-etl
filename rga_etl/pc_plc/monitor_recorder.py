"""Subscribe to the PLC status topics and save them as JSON files for the dashboard."""

import os
import json

import paho.mqtt.client as mqtt

# -------------------------
# Config
# -------------------------
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MONITOR_DIR = os.getenv("MONITOR_DIR", "/app/data")

# Topic published by the PLC -> JSON file read by monitor/index.html
TOPIC_FILES = {
    "monitor/pv": "pv_status.json",
    "monitor/sensor": "sensor_status.json",
    "monitor/bptp": "bptp_status.json",
}

# Status storage
status: dict[str, dict] = {topic: {} for topic in TOPIC_FILES}


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        for topic in TOPIC_FILES:
            client.subscribe(topic)
    else:
        print(f"Connection failed with code {rc}")


def save_status_to_file(topic, data):
    """Safely save status to JSON file."""
    if topic not in TOPIC_FILES:
        return
    filename = os.path.join(MONITOR_DIR, TOPIC_FILES[topic])

    try:
        temp_filename = filename + ".tmp"
        with open(temp_filename, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_filename, filename)
    except IOError as e:
        print(f"Failed to write to {filename}: {e}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data_dict = json.loads(payload)
        print(f"Topic: {msg.topic}")
        print(f"Data: {data_dict}")

        # Update status
        if msg.topic in TOPIC_FILES:
            status[msg.topic] = data_dict
            save_status_to_file(msg.topic, data_dict)

    except json.JSONDecodeError:
        print(f"Failed to decode JSON from {msg.topic}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 1)
    client.loop_forever()


if __name__ == "__main__":
    main()
