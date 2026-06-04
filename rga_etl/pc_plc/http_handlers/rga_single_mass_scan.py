import json

from rga_etl.pc_plc.http_handlers.shared import DEFAULT_TIMEOUT, INIT_COMMANDS, END_COMMANDS


def handle_single_mass_scan(req, data, publish, subscribe):
    try:
        mass = int(data["MR"])
    except (KeyError, ValueError) as e:
        req._reject(400, str(e))
        return

    try:
        req._run_commands(INIT_COMMANDS, publish, subscribe)
        responses = req._run_commands(
            [
                {
                    "rga/command": f"MR{mass}\r",
                    "nocommand": 0,
                    "noresponse": 0,
                    "length": 4,
                    "timeout": DEFAULT_TIMEOUT,
                }
            ],
            publish,
            subscribe,
        )
        req._run_commands(END_COMMANDS, publish, subscribe)
    except TimeoutError as e:
        req._reject(500, str(e))
        return

    req._set_headers(200)
    req.wfile.write(json.dumps({"status": "ok", "mass": mass, "intensity": responses[0]}).encode())
