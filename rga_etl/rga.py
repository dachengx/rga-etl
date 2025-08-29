from srsinst.rga import RGA100


def init_rga():
    usb_serial_device_identifier = "/dev/tty.usbserial-FTEIZFXM"
    baud_rate = 28800

    rga = RGA100("serial", usb_serial_device_identifier, baud_rate)
    return rga


def set_rga(rga):
    rga.scan.initial_mass = 1
    rga.scan.final_mass = 200
    rga.scan.resolution = 10
    rga.scan.scan_speed = 3
    return rga
