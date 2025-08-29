import os
from dotenv import load_dotenv
from srsinst.rga import RGA100


def init_rga():
    load_dotenv()
    usb_serial_device_identifier = os.getenv(
        "RGA_USB_SERIAL_DEVICE_IDENTIFIER", "/dev/tty.usbserial-FTEIZFXM"
    )
    baud_rate = int(os.getenv("RGA_BAUD_RATE", "28800"))

    rga = RGA100("serial", usb_serial_device_identifier, baud_rate)
    return rga


def set_rga(rga):
    rga.scan.initial_mass = int(os.getenv("RGA_INITIAL_MASS", "1"))
    rga.scan.final_mass = int(os.getenv("RGA_FINAL_MASS", "200"))
    rga.scan.resolution = int(os.getenv("RGA_RESOLUTION", "10"))
    rga.scan.scan_speed = int(os.getenv("RGA_SCAN_SPEED", "3"))
