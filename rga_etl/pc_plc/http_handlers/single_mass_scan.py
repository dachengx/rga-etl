import json

from rga_etl.pc_plc.http_handlers.shared import INIT_COMMANDS, END_COMMANDS


class SingleMassScanHandler:
    def _handle_single_mass_scan(self, data):
        try:
            mass = float(data["MR"])
        except (KeyError, ValueError) as e:
            self._reject(400, str(e))
            return

        commands = (
            INIT_COMMANDS
            + [{"main": f"MR{mass}\r", "length": 4, "noresult": 0, "timeout": 1.0}]
            + END_COMMANDS
        )
        self.runner.submit_commands(commands)

        self._set_headers(200)
        self.wfile.write(
            json.dumps(
                {
                    "status": "ok",
                    "message": f"Single mass scan started for mass {mass}",
                }
            ).encode()
        )
