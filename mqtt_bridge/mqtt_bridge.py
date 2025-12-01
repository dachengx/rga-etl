import os
import sys
import json
import signal
import threading
import http.server
import socketserver
import logging

import paho.mqtt.client as mqtt

# -------------------------
# Config
# -------------------------
HTTP_PORT = 8080
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = "brx/control"
GRAFANA_ORIGIN = "http://localhost:3000"

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

# -------------------------
# MQTT setup
# -------------------------
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()
logging.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")


# -------------------------
# HTTP Handler
# -------------------------
class CustomHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Reduce default spam but keep minimal info
        logging.debug("%s - %s" % (self.client_address[0], format % args))

    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", GRAFANA_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_POST(self):
        logging.info(f"POST {self.path} from {self.client_address[0]}")

        # Read request body
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)
            if not raw_body:
                raise ValueError("Empty request body")
            data = json.loads(raw_body.decode("utf-8", errors="ignore"))
            if not isinstance(data, dict):
                raise ValueError("JSON must be an object")
        except Exception as e:
            logging.warning(f"Invalid JSON: {e}")
            self._set_headers(400)
            self.wfile.write(
                json.dumps(
                    {"status": "error", "message": f"Invalid JSON: {e}"}
                ).encode()
            )
            return

        published = []
        errors = []

        # Publish every key/value pair to MQTT
        for key, value in data.items():
            topic = f"{MQTT_TOPIC_PREFIX}/{key}"
            try:
                mqtt_client.publish(topic, str(value))
                published.append(f"{key}: {value}")
            except Exception as e:
                logging.error(f"Failed to publish to {topic}: {e}")
                errors.append({"key": key, "error": str(e)})

        # Respond to Grafana
        self._set_headers(200)
        response = {
            "status": "ok" if not errors else "partial",
            "message": "Published to MQTT" if not errors else "Some keys failed",
            "published_keys": published,
            "errors": errors,
        }

        logging.info(f"Published: {published}  Errors: {errors}")
        self.wfile.write(json.dumps(response).encode())


# -------------------------
# Threaded server
# -------------------------
class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True


def main():
    server = ThreadedHTTPServer(("", HTTP_PORT), CustomHTTPRequestHandler)

    # --- Handle Ctrl+C cleanly ---
    def stop_server(signum, frame):
        logging.info("Ctrl+C detected — shutting down...")

        # 1. Stop HTTP server in a separate thread (prevents deadlock)
        threading.Thread(target=server.shutdown).start()

        # 2. Stop MQTT client cleanly
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logging.info("MQTT client stopped.")

    # Install Ctrl+C handler
    signal.signal(signal.SIGINT, stop_server)

    logging.info(f"HTTP -> MQTT bridge running on port {HTTP_PORT}")
    logging.info("Press Ctrl+C to stop.")

    # Blocking call — stays here until shutdown()
    try:
        # blocks until server.shutdown() is called
        server.serve_forever()
        # After shutdown, serve_forever() returns
        logging.info("HTTP server stopped.")
    finally:
        # always called, even if an exception happens
        logging.info("Closing listening socket...")
        server.server_close()
        logging.info("Socket closed.")



if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Fatal server error: {e}")
        sys.exit(1)
