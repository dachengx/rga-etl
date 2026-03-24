import json
import time
import logging
import threading

from rga_etl.pc_plc.http_handlers.shared import INIT_COMMANDS, END_COMMANDS


def build_measure_commands(masses):
    return [
        {"main": f"MR{mass}\r", "length": 4, "noresult": 0, "timeout": 1.0}
        for mass in sorted(masses)
    ]


class ScanState:
    def __init__(self):
        self._scan_thread = None
        self._stop_scan = threading.Event()

    def is_running(self):
        return self._scan_thread is not None and self._scan_thread.is_alive()

    def start(self, runner, build_cycle_commands, masses, total_time, time_interval):
        self._stop_scan.clear()
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            args=(runner, build_cycle_commands, masses, total_time, time_interval),
            daemon=True,
        )
        self._scan_thread.start()

    def _scan_loop(self, runner, build_cycle_commands, masses, total_time, time_interval):
        n_cycles = int(total_time / time_interval)
        logging.info(
            f"Scan started — masses={masses}, total_time={total_time}s, "
            f"interval={time_interval}s, cycles={n_cycles}"
        )
        scan_start = time.time()

        runner.submit_commands(INIT_COMMANDS)
        runner.command_queue.join()

        for i in range(n_cycles):
            if self._stop_scan.is_set():
                break

            cycle_start = time.time()
            logging.info(f"Cycle {i + 1}/{n_cycles} — measuring masses {masses}")
            runner.submit_commands(build_cycle_commands(masses))
            runner.command_queue.join()

            elapsed = time.time() - cycle_start
            if elapsed > time_interval:
                logging.warning(
                    f"Cycle {i + 1} took {elapsed:.1f}s, longer than interval {time_interval}s"
                )
            else:
                self._stop_scan.wait(timeout=time_interval - elapsed)

        runner.submit_commands(END_COMMANDS)
        runner.command_queue.join()

        total_elapsed = time.time() - scan_start
        if total_elapsed > total_time:
            logging.warning(
                f"Scan took {total_elapsed:.1f}s, longer than assigned total_time {total_time}s"
            )
        logging.info("Scan loop finished.")

    def stop(self):
        self._stop_scan.set()


scan_state = ScanState()


class PvsTScanHandler:
    scan_state = scan_state

    def _handle_pvs_t_scan(self, data):
        try:
            masses = data["MR"]
            total_time = float(data["TOTALTIME"])
            time_interval = float(data["TIMEINTERVAL"])
            if not isinstance(masses, list) or len(masses) == 0:
                raise ValueError("MR must be a non-empty list of masses")
        except (KeyError, ValueError) as e:
            self._reject(400, str(e))
            return

        self.scan_state.start(
            self.runner, build_measure_commands, masses, total_time, time_interval
        )

        self._set_headers(200)
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "message": f"Scan started for masses {masses}",
                }
            ).encode()
        )
