import json


class ArbitraryCommandHandler:
    def _handle_arbitrary_command(self, data):
        try:
            command = str(data["COMMAND"])
            length = int(data["LENGTH"])
            noresult = int(data["WITH_RESULT"])
            timeout = float(data["TIMEOUT"])
            if not command.endswith("\r"):
                command += "\r"
        except (KeyError, ValueError) as e:
            self._reject(400, str(e))
            return

        self.runner.submit_commands(
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
