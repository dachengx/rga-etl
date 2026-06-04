from srsinst.rga.instruments.rga100.components import Pressure

# When the length is updated, RGAControl.json should be updated to match.
DEFAULT_RESPONSE_LENGTH = 256
DEFAULT_TIMEOUT = 1.0

INIT_COMMANDS = [
    {
        "rga/command": "ID?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "IN0\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "FL1.0\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": 10.0,
    },
]

END_COMMANDS = [
    {
        "rga/command": "MR0\r",
        "nocommand": 0,
        "noresponse": 1,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "FL0.0\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": 10.0,
    },
]

# Query RGA instrument parameters after filament is on.
# Results order: EE, IE, VF, FL, SP, ST, TP
PARAM_COMMANDS = [
    {
        "rga/command": "EE?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "IE?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "VF?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "FL?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "SP?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "ST?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": DEFAULT_RESPONSE_LENGTH,
        "timeout": DEFAULT_TIMEOUT,
    },
    {
        "rga/command": "TP?\r",
        "nocommand": 0,
        "noresponse": 0,
        "length": 4,
        "timeout": 10.0,
    },
]

# Assumed FC (Faraday Cup) detector — no CEM gain correction applied.
# Assumed no UGA inlet — reduction_factor = 1.0 (omitted).


def fill_execution_params(execution, param_results):
    """Populate an Execution object from PARAM_COMMANDS responses.

    Mirrors set_rga_parameters_to_execution() in rga_etl/pc/rga.py,
    which calls rga.pressure.get_total_pressure_in_torr() and
    rga.pressure.get_partial_pressure_sensitivity_in_torr() from:
    https://github.com/thinkSRS/srsinst.rga/blob/main/srsinst/rga/instruments/rga100/components.py

    """
    if len(param_results) != len(PARAM_COMMANDS):
        raise ValueError(
            f"Expected {len(PARAM_COMMANDS)} param responses, got {len(param_results)}"
        )

    # Clamp sensitivities to LowLimit to avoid division by near-zero.
    # Mirrors: sp = Pressure.LowLimit if sp < Pressure.LowLimit else sp (line ~202)
    sp = max(param_results[4], Pressure.LowLimit)  # SP: partial pressure sensitivity (mA/Torr)
    st = max(param_results[5], Pressure.LowLimit)  # ST: total pressure sensitivity (mA/Torr)

    execution.detector = "FC"
    execution.electron_energy = param_results[0]  # EE
    execution.ion_energy = param_results[1]  # IE (already converted to 8 or 12 eV)
    execution.focus_voltage = param_results[2]  # VF
    execution.emission_current = param_results[3]  # FL

    # total_pressure: TP (binary long, 0.1 fA units) * 1e-13 / ST
    # Mirrors: return self.total_pressure * factor (line ~192)
    execution.total_pressure = param_results[6] * 1e-13 / st

    # partial_pressure_sensitivity_factor: 1e-13 / SP
    # Mirrors: factor = 1e-13 / sp / self.reduction_factor (line ~211), reduction_factor = 1.0
    execution.partial_pressure_sensitivity_factor = 1e-13 / sp
