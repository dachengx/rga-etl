import os
import sys
import json
import time
import signal
import threading
import http.server
import socketserver
import logging

from rga_etl.pc_plc.mqtt_runner import MQTTCommandRunner

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


# -------------------------
# Command builder
# -------------------------
INIT_COMMANDS = [
    {"main": "ID?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "IN0\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "FL1.0\r", "length": 128, "noresult": 0, "timeout": 10.0},
]

END_COMMANDS = [
    {"main": "MR0\r", "length": 128, "noresult": 1, "timeout": 1.0},
    {"main": "FL0.0\r", "length": 128, "noresult": 0, "timeout": 10.0},
]


def build_measure_commands(masses):
    return [
        {"main": f"MR{mass}\r", "length": 4, "noresult": 0, "timeout": 1.0}
        for mass in sorted(masses)
    ]


# -------------------------
# Scan controller
# -------------------------
class ScanController:
    def __init__(self):
        self._scan_thread = None
        self._stop_scan = threading.Event()
        self.runner = MQTTCommandRunner(
            broker=MQTT_BROKER,
            port=MQTT_PORT,
            topic_prefix=MQTT_TOPIC_PREFIX,
        )
        self.runner.connect()

    def is_running(self):
        return self._scan_thread is not None and self._scan_thread.is_alive()

    def start_scan(self, masses, total_time, time_interval):
        self._stop_scan.clear()
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            args=(masses, total_time, time_interval),
            daemon=True,
        )
        self._scan_thread.start()

    def _scan_loop(self, masses, total_time, time_interval):
        n_cycles = int(total_time / time_interval)
        logging.info(
            f"Scan started — masses={masses}, total_time={total_time}s, "
            f"interval={time_interval}s, cycles={n_cycles}"
        )
        scan_start = time.time()

        self.runner.submit_commands(INIT_COMMANDS)
        self.runner.command_queue.join()

        for i in range(n_cycles):
            if self._stop_scan.is_set():
                break

            cycle_start = time.time()
            logging.info(f"Cycle {i + 1}/{n_cycles} — measuring masses {masses}")
            self.runner.submit_commands(build_measure_commands(masses))

            # Wait for all commands to finish
            self.runner.command_queue.join()

            elapsed = time.time() - cycle_start
            if elapsed > time_interval:
                logging.warning(
                    f"Cycle {i + 1} took {elapsed:.1f}s, longer than interval {time_interval}s"
                )
            else:
                self._stop_scan.wait(timeout=time_interval - elapsed)

        self.runner.submit_commands(END_COMMANDS)
        self.runner.command_queue.join()

        total_elapsed = time.time() - scan_start
        if total_elapsed > total_time:
            logging.warning(
                f"Scan took {total_elapsed:.1f}s, longer than assigned total_time {total_time}s"
            )
        logging.info("Scan loop finished.")

    def stop(self):
        self._stop_scan.set()
        self.runner.disconnect()


# -------------------------
# HTTP Handler
# -------------------------
scan_controller = ScanController()


class CustomHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
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

        # Parse request body
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
                json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}).encode()
            )
            return

        if self.path == "/p_vs_t_scan":
            self._handle_pvs_t_scan(data)
        elif self.path == "/single_mass_scan":
            self._handle_single_mass_scan(data)
        elif self.path == "/analog_scan":
            self._handle_analog_scan(data)
        elif self.path == "/arbitrary_command":
            self._handle_arbitrary_command(data)
        else:
            logging.warning(f"Unknown endpoint: {self.path}")
            self._set_headers(404)
            self.wfile.write(
                json.dumps(
                    {"status": "error", "message": f"Unknown endpoint: {self.path}"}
                ).encode()
            )

    def _handle_pvs_t_scan(self, data):
        try:
            masses = data["MR"]
            total_time = float(data["TOTALTIME"])
            time_interval = float(data["TIMEINTERVAL"])
            if not isinstance(masses, list) or len(masses) == 0:
                raise ValueError("MR must be a non-empty list of masses")
        except (KeyError, ValueError) as e:
            logging.warning(f"Invalid payload: {e}")
            self._set_headers(400)
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
            return

        if scan_controller.is_running():
            logging.error("Scan already running — rejecting new command.")
            self._set_headers(409)
            self.wfile.write(
                json.dumps(
                    {
                        "status": "error",
                        "message": "Scan already running. Wait for it to finish.",
                    }
                ).encode()
            )
            return

        scan_controller.start_scan(masses, total_time, time_interval)

        self._set_headers(200)
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "message": f"Scan started for masses {masses}",
                }
            ).encode()
        )

    def _handle_single_mass_scan(self, data):
        try:
            mass = float(data["MR"])
        except (KeyError, ValueError) as e:
            logging.warning(f"Invalid payload: {e}")
            self._set_headers(400)
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
            return

        if scan_controller.runner.is_busy():
            logging.error("Runner busy — rejecting new command.")
            self._set_headers(409)
            self.wfile.write(
                json.dumps(
                    {
                        "status": "error",
                        "message": "Runner busy. Wait for it to finish.",
                    }
                ).encode()
            )
            return

        commands = (
            INIT_COMMANDS
            + [{"main": f"MR{mass}\r", "length": 4, "noresult": 0, "timeout": 1.0}]
            + END_COMMANDS
        )
        scan_controller.runner.submit_commands(commands)

        self._set_headers(200)
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "message": f"Single mass scan started for mass {mass}",
                }
            ).encode()
        )

    def _handle_analog_scan(self, data):
        try:
            initial_mass = int(data["INITIAL_MASS"])
            final_mass = int(data["FINAL_MASS"])
            scan_rate = int(data["SCAN_RATE"])
            steps_per_amu = int(data["STEPS_PER_AMU"])
            if not (1 <= initial_mass < final_mass):
                raise ValueError(
                    "INITIAL_MASS must be < FINAL_MASS and >= 1 "
                    f"(got INITIAL_MASS={initial_mass}, FINAL_MASS={final_mass})"
                )
            if not (0 <= scan_rate <= 7):
                raise ValueError(f"SCAN_RATE must be between 0 and 7 (got {scan_rate})")
            if not (10 <= steps_per_amu <= 25):
                raise ValueError(f"STEPS_PER_AMU must be between 10 and 25 (got {steps_per_amu})")
        except (KeyError, ValueError) as e:
            logging.warning(f"Invalid payload: {e}")
            self._set_headers(400)
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
            return

        if scan_controller.runner.is_busy():
            logging.error("Runner busy — rejecting new command.")
            self._set_headers(409)
            self.wfile.write(
                json.dumps(
                    {
                        "status": "error",
                        "message": "Runner busy. Wait for it to finish.",
                    }
                ).encode()
            )
            return

        # There is a last byte in the response of SC comand that indicates the total pressure
        n = (final_mass - initial_mass) * steps_per_amu + 1
        logging.info(f"Analog scan: n={n} data points")
        commands = [
            {"main": f"MI{initial_mass}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": f"MF{final_mass}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": f"NF{scan_rate}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": f"SA{steps_per_amu}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": f"AP?\r", "length": 128, "noresult": 0, "timeout": 1.0},
            {"main": f"SC1\r", "length": (n + 1) * 4, "noresult": 0, "timeout": 10.0},
        ]
        commands = INIT_COMMANDS + commands + END_COMMANDS
        scan_controller.runner.submit_commands(commands)

        self._set_headers(200)
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "message": f"Analog scan started: mass {initial_mass}-{final_mass}, {n} points",
                }
            ).encode()
        )

    def _handle_arbitrary_command(self, data):
        try:
            command = str(data["COMMAND"])
            length = int(data["LENGTH"])
            noresult = int(data["WITH_RESULT"])
            timeout = float(data["TIMEOUT"])
            if not command.endswith("\r"):
                command += "\r"
        except (KeyError, ValueError) as e:
            logging.warning(f"Invalid payload: {e}")
            self._set_headers(400)
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
            return

        scan_controller.runner.submit_commands(
            [{"main": command, "length": length, "noresult": noresult, "timeout": timeout}]
        )

        self._set_headers(200)
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "message": f"Command sent: {command!r}",
                }
            ).encode()
        )


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
        scan_controller.stop()
        logging.info("Scan controller stopped.")

    signal.signal(signal.SIGINT, stop_server)

    logging.info(f"HTTP -> RGA bridge running on port {HTTP_PORT}")
    logging.info("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
        logging.info("HTTP server stopped.")
    finally:
        logging.info("Closing listening socket...")
        server.server_close()
        logging.info("Socket closed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Fatal server error: {e}")
        sys.exit(1)
