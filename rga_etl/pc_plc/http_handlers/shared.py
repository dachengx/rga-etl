from srsinst.rga.instruments.rga100.components import Pressure

INIT_COMMANDS = [
    {"main": "ID?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "IN0\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "FL1.0\r", "length": 128, "noresult": 0, "timeout": 10.0},
]

END_COMMANDS = [
    {"main": "MR0\r", "length": 128, "noresult": 1, "timeout": 1.0},
    {"main": "FL0.0\r", "length": 128, "noresult": 0, "timeout": 10.0},
]

# Query RGA instrument parameters after filament is on.
# Results order: EE, IE, VF, FL, SP, ST, TP
PARAM_COMMANDS = [
    {"main": "EE?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "IE?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "VF?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "FL?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "SP?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "ST?\r", "length": 128, "noresult": 0, "timeout": 1.0},
    {"main": "TP?\r", "length": 4, "noresult": 0, "timeout": 1.0},
]

# Assumed FC (Faraday Cup) detector — no CEM gain correction applied.
# Assumed no UGA inlet — reduction_factor = 1.0.
_REDUCTION_FACTOR_MIN = 1e-12


def fill_execution_params(execution, param_results):
    """Populate an Execution object from PARAM_COMMANDS results.

    Mirrors set_rga_parameters_to_execution() in rga_etl/pc/rga.py,
    which calls rga.pressure.get_total_pressure_in_torr() and
    rga.pressure.get_partial_pressure_sensitivity_in_torr() from:
    https://github.com/thinkSRS/srsinst.rga/blob/main/srsinst/rga/instruments/rga100/components.py

    """
    # Clamp sensitivities to LowLimit to avoid division by near-zero.
    # Mirrors: sp = Pressure.LowLimit if sp < Pressure.LowLimit else sp (line ~202)
    sp = max(param_results[4], Pressure.LowLimit)  # SP: partial pressure sensitivity (mA/Torr)
    st = max(param_results[5], Pressure.LowLimit)  # ST: total pressure sensitivity (mA/Torr)

    # Mirrors: if self.reduction_factor < 1e-12: self.reduction_factor = 1e-12 (line ~205)
    reduction_factor = max(1.0, _REDUCTION_FACTOR_MIN)

    execution.detector = "FC"
    execution.electron_energy = param_results[0]  # EE
    execution.ion_energy = param_results[1]  # IE (already converted to 8 or 12 eV)
    execution.focus_voltage = param_results[2]  # VF
    execution.emission_current = param_results[3]  # FL

    # total_pressure: TP (binary long, 0.1 fA units) * 1e-13 / ST
    # Mirrors: return self.total_pressure * factor (line ~192)
    execution.total_pressure = param_results[6] * 1e-13 / st

    # partial_pressure_sensitivity_factor: 1e-13 / SP / reduction_factor
    # Mirrors: factor = 1e-13 / sp / self.reduction_factor (line ~211)
    execution.partial_pressure_sensitivity_factor = 1e-13 / sp / reduction_factor
