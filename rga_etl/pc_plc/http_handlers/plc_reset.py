import json


def handle_reset(req, data, publish, subscribe):
    try:
        req._run_commands([{"noresult": 1, "timeout": 1.0}], publish, subscribe)
    except TimeoutError as e:
        req._reject(500, str(e))
        return

    req._set_headers(200)
    req.wfile.write(json.dumps({"status": "ok", "message": "PLC reset complete"}).encode())
