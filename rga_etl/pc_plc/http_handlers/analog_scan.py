import json
import logging

from rga_etl.pc_plc.http_handlers.shared import INIT_COMMANDS, END_COMMANDS


class AnalogScanHandler:
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
            self._reject(400, str(e))
            return

        # There is a last byte in the response of SC command that indicates the total pressure
        n = (final_mass - initial_mass) * steps_per_amu + 1
        logging.info(f"Analog scan: n={n} data points")
        commands = [
            {"main": f"MI{initial_mass}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": f"MF{final_mass}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": f"NF{scan_rate}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": f"SA{steps_per_amu}\r", "length": 128, "noresult": 1, "timeout": 1.0},
            {"main": "AP?\r", "length": 128, "noresult": 0, "timeout": 1.0},
            {"main": "SC1\r", "length": (n + 1) * 4, "noresult": 0, "timeout": 10.0},
        ]
        self.runner.submit_commands(INIT_COMMANDS + commands + END_COMMANDS)

        self._set_headers(200)
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "message": f"Analog scan started: mass {initial_mass}-{final_mass}, {n} points",
                }
            ).encode()
        )
