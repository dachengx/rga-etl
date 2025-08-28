import time
from srsinst.rga import RGA100


# the RGA name might change when connect to anothe DTE or reconnect to the same DTE

usb_serial_device_identifier = "/dev/tty.usbserial-FTEIZFXM"
baud_rate = 28800

rga = RGA100("serial", usb_serial_device_identifier, baud_rate)

# rga = RGA100()
# rga.connect('serial', usb_serial_device_identifier, baud_rate)

rga.ionizer.emission_current = 1.0  # in the unit of mA
# rga.ionizer.emission_current = 0.0  # will turn off the filament

# rga.filament.turn_on()  # turn on with the default emission current of 1 mA.
# rga.filament.turn_off()

rga.scan.initial_mass = 1
rga.scan.final_mass = 140
rga.scan.scan_speed = 3
rga.scan.resolution = 10  # steps_per_amu

# run an analog scan

start = time.time()
analog_spectrum = rga.scan.get_analog_scan()
end = time.time()
print("Analog scan took {:.2f} seconds".format(end - start))

spectrum_in_torr = rga.scan.get_partial_pressure_corrected_spectrum(analog_spectrum)

# get the matching mass axis with the spectrum
analog_mass_axis = rga.scan.get_mass_axis(True)  # is it for analog scan? Yes

with open("spectrum.dat", "w") as f:
    for x, y in zip(analog_mass_axis, analog_spectrum):
        f.write("{:.2f} {:.4e}\n".format(x, y))

# measure a single mass ion current of nitrogen at 28 amu
intensity = rga.scan.get_single_mass_scan(28)
