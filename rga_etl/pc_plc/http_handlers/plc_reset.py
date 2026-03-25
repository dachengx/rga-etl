import json

from rga_etl.pc_plc.http_handlers.shared import DEFAULT_TIMEOUT


def handle_reset(req, data, publish, subscribe):
    try:
        req._run_commands([{"noresult": 1, "timeout": DEFAULT_TIMEOUT}], publish, subscribe)
    except TimeoutError as e:
        req._reject(500, str(e))
        return

    req._set_headers(200)
    req.wfile.write(json.dumps({"status": "ok", "message": "PLC reset complete"}).encode())
