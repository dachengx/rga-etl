import json

from rga_etl.pc_plc.http_handlers.shared import INIT_COMMANDS, END_COMMANDS


class SingleMassScanHandler:
    def _handle_single_mass_scan(self, data):
        try:
            mass = float(data["MR"])
        except (KeyError, ValueError) as e:
            self._reject(400, str(e))
            return

        self.runner.run_commands(INIT_COMMANDS)
        results = self.runner.run_commands(
            [{"main": f"MR{mass}\r", "length": 4, "noresult": 0, "timeout": 1.0}]
        )
        self.runner.run_commands(END_COMMANDS)

        self._set_headers(200)
        self.wfile.write(
            json.dumps({"status": "ok", "mass": mass, "intensity": results[0]}).encode()
        )
