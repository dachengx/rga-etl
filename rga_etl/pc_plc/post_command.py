# Post-command response processors for RGA MQTT responses.
# Source reference for command semantics:
# https://github.com/thinkSRS/srsinst.rga/blob/main/srsinst/rga/instruments/rga100/components.py
# https://github.com/thinkSRS/srsinst.rga/blob/main/srsinst/rga/instruments/rga100/scans.py

from srsinst.rga.instruments.rga100.scans import Scans


def _ascii_int(payload):
    try:
        return int(payload.decode().strip())
    except (UnicodeDecodeError, ValueError) as e:
        raise ValueError(f"Failed to parse ASCII int from payload {payload!r}: {e}") from e


def _ascii_float(payload):
    try:
        return float(payload.decode().strip())
    except (UnicodeDecodeError, ValueError) as e:
        raise ValueError(f"Failed to parse ASCII float from payload {payload!r}: {e}") from e


def _handle_ie(payload):
    # IE? returns 0 or 1; Ionizer.ion_energy maps: 0 -> 8 eV, 1 -> 12 eV
    # Mirrors: lambda a: 12 if int(a) != 0 else 8  (RgaIonEnergyCommand)
    return 12 if _ascii_int(payload) != 0 else 8


def _handle_sc(payload):
    # SC1 returns n+1 little-endian signed 32-bit integers; last one is total current.
    # Mirrors: Scans.convert_to_long used in get_analog_scan()
    return [
        Scans.convert_to_long(payload[i : i + 4])
        for i in range(0, len(payload), 4)
        if len(payload[i : i + 4]) == 4
    ]


_HANDLERS = {
    # MR{mass}: single-mass ion current, 4-byte little-endian signed int (0.1 fA)
    # Mirrors: Scans.get_single_mass_scan() -> comm._read_binary(4) -> convert_to_long
    "MR": Scans.convert_to_long,
    # SC1: analog scan, (n+1) * 4 bytes; last 4 bytes are total current
    "SC": _handle_sc,
    # TP?: total pressure ion current, 4-byte little-endian signed int (0.1 fA)
    # Mirrors: RgaTotalPressureCommand.__get__() -> comm._read_long()
    "TP?": Scans.convert_to_long,
    # AP?: number of data points expected in next analog scan (ASCII int)
    # Mirrors: Scans.total_points_analog = IntGetCommand('AP')
    "AP?": _ascii_int,
    # EE?: electron energy in eV (ASCII int, range 25-105)
    # Mirrors: Ionizer.electron_energy = RgaIntCommand('EE')
    "EE?": _ascii_int,
    # VF?: focus plate voltage in V (ASCII int, range 0-150)
    # Mirrors: Ionizer.focus_voltage = RgaIntCommand('VF')
    "VF?": _ascii_int,
    # FL?: filament emission current in mA (ASCII float, range 0.0-3.5)
    # Mirrors: Ionizer.emission_current = RgaFloatCommand('FL')
    "FL?": _ascii_float,
    # SP?: partial pressure sensitivity in mA/Torr (ASCII float)
    # Mirrors: Pressure.partial_pressure_sensitivity = FloatNSCommand('SP')
    "SP?": _ascii_float,
    # ST?: total pressure sensitivity in mA/Torr (ASCII float)
    # Mirrors: Pressure.total_pressure_sensitivity = FloatNSCommand('ST')
    "ST?": _ascii_float,
    # IE?: ion energy; returns 0 (8 eV) or 1 (12 eV), converted to actual eV
    # Mirrors: Ionizer.ion_energy = RgaIonEnergyCommand('IE')
    "IE?": _handle_ie,
}


def process(command, payload):
    """Apply post-command processing to a raw MQTT response payload.

    Looks up the command's 'main' field against registered prefixes. Falls back to UTF-8 decode if
    no handler matches.

    """
    main = command.get("rga/command", "")
    for prefix, handler in _HANDLERS.items():
        if main.startswith(prefix):
            return handler(payload)
    return payload.decode("utf-8", errors="replace")
