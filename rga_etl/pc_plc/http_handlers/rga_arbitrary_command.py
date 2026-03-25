import json


def handle_arbitrary_command(req, data, publish, subscribe):
    try:
        command = str(data["COMMAND"])
        length = int(data["LENGTH"])
        noresponse = 1 - int(data["WITH_RESULT"])  # WITH_RESULT=1 (Yes) → noresponse=0
        timeout = float(data["TIMEOUT"])
        if not command.endswith("\r"):
            command += "\r"
    except (KeyError, ValueError) as e:
        req._reject(400, str(e))
        return

    try:
        responses = req._run_commands(
            [
                {
                    "rga/command": command,
                    "length": length,
                    "noresponse": noresponse,
                    "timeout": timeout,
                }
            ],
            publish,
            subscribe,
        )
    except TimeoutError as e:
        req._reject(500, str(e))
        return

    req._set_headers(200)
    req.wfile.write(
        json.dumps({"status": "ok", "command": command, "response": responses[0]}).encode()
    )
