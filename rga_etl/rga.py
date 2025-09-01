import os
from dotenv import load_dotenv
from srsinst.rga import RGA100


def init_rga():
    """Initialize the RGA100 device with parameters from environment variables.
    Returns:
        RGA100: An instance of the RGA100 class.
    """
    load_dotenv()
    usb_serial_device_identifier = os.getenv(
        "RGA_USB_SERIAL_DEVICE_IDENTIFIER", "/dev/tty.usbserial-FTEIZFXM"
    )
    baud_rate = int(os.getenv("RGA_BAUD_RATE", "28800"))

    rga = RGA100("serial", usb_serial_device_identifier, baud_rate)
    return rga


def set_rga_analog_scan_parameters(rga):
    """Set the RGA100 analog scan parameters from environment variables.
    Args:
        rga (RGA100): An instance of the RGA100 class.
    """
    rga.scan.initial_mass = int(os.getenv("RGA_INITIAL_MASS", "1"))
    rga.scan.final_mass = int(os.getenv("RGA_FINAL_MASS", "200"))
    rga.scan.resolution = int(os.getenv("RGA_RESOLUTION", "10"))
    rga.scan.scan_speed = int(os.getenv("RGA_SCAN_SPEED", "3"))


def set_rga_parameters_to_execution(rga, execution):
    """Set RGA parameters to the execution object.
    Make sure this is called after initializing the filament.
    Args:
        rga (RGA100): An instance of the RGA100 class.
        execution (Execution): An instance of the Execution class.
    """
    execution.detector = "FC"
    execution.electron_energy = rga.ionizer.electron_energy
    execution.ion_energy = rga.ionizer.ion_energy
    execution.focus_voltage = rga.ionizer.focus_voltage
    execution.emission_current = rga.ionizer.emission_current
    execution.total_pressure = rga.pressure.get_total_pressure_in_torr()
    execution.partial_pressure_sensitivity_factor = (
        rga.pressure.get_partial_pressure_sensitivity_in_torr()
    )


def rga_turn_off_filament():
    """Turn off the RGA filament if it is on.
    This function is useful to ensure the filament is turned off
    in case of an unexpected error during execution.
    """
    load_dotenv()
    fake = os.getenv("FAKE_EXECUTION", "0") == "1"
    if fake:
        return
    rga = init_rga()
    rga.filament.turn_off()
