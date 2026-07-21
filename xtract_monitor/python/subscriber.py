import paho.mqtt.client as mqtt
import json
import os

# MQTT broker configuration
BROKER = "169.254.1.106"
PORT = 1883
TOPICS = ["XTRACT/PV", "XTRACT/SENSOR"]

# Status storage
status: dict[str, dict] = {"XTRACT/PV": {}, "XTRACT/SENSOR": {}}


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        for topic in TOPICS:
            client.subscribe(topic)
    else:
        print(f"Connection failed with code {rc}")


def save_status_to_file(topic, data):
    """Safely save status to JSON file."""
    if topic == "XTRACT/PV":
        filename = "/app/data/pv_status.json"
    elif topic == "XTRACT/SENSOR":
        filename = "/app/data/sensor_status.json"
    else:
        return

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
        if msg.topic == "XTRACT/PV":
            status["XTRACT/PV"] = data_dict
            save_status_to_file("XTRACT/PV", data_dict)
        elif msg.topic == "XTRACT/SENSOR":
            status["XTRACT/SENSOR"] = data_dict
            save_status_to_file("XTRACT/SENSOR", data_dict)

    except json.JSONDecodeError:
        print(f"Failed to decode JSON from {msg.topic}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 1)
client.loop_forever()
