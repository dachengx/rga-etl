import json


class ArbitraryCommandHandler:
    def _handle_arbitrary_command(self, data):
        try:
            command = str(data["COMMAND"])
            length = int(data["LENGTH"])
            noresult = 1 - int(data["WITH_RESULT"])  # WITH_RESULT=1 (Yes) → noresult=0
            timeout = float(data["TIMEOUT"])
            if not command.endswith("\r"):
                command += "\r"
        except (KeyError, ValueError) as e:
            self._reject(400, str(e))
            return

        try:
            results = self.runner.run_commands(
                [{"main": command, "length": length, "noresult": noresult, "timeout": timeout}]
            )
        except TimeoutError as e:
            self._reject(500, str(e))
            return

        self._set_headers(200)
        self.wfile.write(
            json.dumps({"status": "ok", "command": command, "result": results[0]}).encode()
        )
