import os
import sys
import json
import signal
import threading
import http.server
import socketserver
import logging

from rga_etl.pc_plc.mqtt_runner import MQTTCommandRunner
from rga_etl.pc_plc.http_handlers.rga_p_vs_t_scan import handle_p_vs_t_scan, scan_state
from rga_etl.pc_plc.http_handlers.rga_single_mass_scan import handle_single_mass_scan
from rga_etl.pc_plc.http_handlers.rga_analog_scan import handle_analog_scan
from rga_etl.pc_plc.http_handlers.arbitrary_command import handle_arbitrary_command
from rga_etl.pc_plc.http_handlers.plc_reset import handle_reset

# -------------------------
# Config
# -------------------------
HTTP_PORT = 8080
MQTT_BROKER = os.getenv("MQTT_BROKER", "169.254.11.119")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = "brx/control"
GRAFANA_ORIGIN = "http://localhost:3000"

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logging.getLogger("mysql.connector").setLevel(logging.WARNING)

runner = MQTTCommandRunner(
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    topic_prefix=MQTT_TOPIC_PREFIX,
)
runner.connect()


# -------------------------
# HTTP Handler
# -------------------------
class CustomHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    runner = runner

    _ROUTES = {
        "/p_vs_t_scan": {
            "handler": handle_p_vs_t_scan,
            "publish": "generic",
            "subscribe": "result",
        },
        "/single_mass_scan": {
            "handler": handle_single_mass_scan,
            "publish": "generic",
            "subscribe": "result",
        },
        "/analog_scan": {
            "handler": handle_analog_scan,
            "publish": "generic",
            "subscribe": "result",
        },
        "/arbitrary_command": {
            "handler": handle_arbitrary_command,
            "publish": "generic",
            "subscribe": "result",
        },
        "/reset": {
            "handler": handle_reset,
            "publish": "reset",
            "subscribe": "result",
        },
    }

    def _run_commands(self, commands, publish, subscribe):
        decorated = [{"publish": publish, "subscribe": subscribe, **cmd} for cmd in commands]
        return self.runner.run_commands(decorated)

    def log_message(self, format, *args):
        logging.debug("%s - %s" % (self.client_address[0], format % args))

    def _reject(self, status, message):
        logging.warning(f"Rejected ({status}): {message}")
        self._set_headers(status)
        self.wfile.write(json.dumps({"status": "error", "message": message}).encode())

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

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)
            if not raw_body:
                raise ValueError("Empty request body")
            data = json.loads(raw_body.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON must be an object")
        except Exception as e:
            self._reject(400, f"Invalid JSON: {e}")
            return

        busy_reason = (
            "Scan running"
            if scan_state.is_running()
            else "Runner busy" if runner.is_busy() else None
        )
        if busy_reason:
            self._reject(409, f"{busy_reason}. Wait for it to finish.")
            return

        route = self._ROUTES.get(self.path)
        if route:
            try:
                route["handler"](self, data, route["publish"], route["subscribe"])
            except TimeoutError as e:
                self._reject(500, str(e))
        else:
            self._reject(404, f"Unknown endpoint: {self.path}")


# -------------------------
# Threaded server
# -------------------------
class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    server = ThreadedHTTPServer(("", HTTP_PORT), CustomHTTPRequestHandler)

    def stop_server(signum, frame):
        logging.info("Ctrl+C detected — shutting down...")
        threading.Thread(target=server.shutdown).start()

    signal.signal(signal.SIGINT, stop_server)

    logging.info(f"HTTP -> RGA bridge running on port {HTTP_PORT}")
    logging.info("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
        logging.info("HTTP server stopped.")
    finally:
        scan_state.stop()
        runner.disconnect()
        logging.info("Runner stopped.")
        logging.info("Closing listening socket...")
        server.server_close()
        logging.info("Socket closed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Fatal server error: {e}")
        sys.exit(1)
