from srsinst.rga.instruments.rga100.scans import Scans


# -------------------------
# Post-command handlers
# Maps command prefix -> function(raw bytes) -> processed result
# -------------------------
def _handle_mr(payload):
    return Scans.convert_to_long(payload)


_HANDLERS = {
    "MR": _handle_mr,
}


def process(command, payload):
    """Apply post-command processing to a raw MQTT result payload.

    Looks up the command's 'main' field against registered prefixes. Falls back to UTF-8 decode if
    no handler matches.

    """
    main = command.get("main", "")
    for prefix, handler in _HANDLERS.items():
        if main.startswith(prefix):
            return handler(payload)
    return payload.decode("utf-8", errors="replace")
