import time
import math
from types import SimpleNamespace
import datetime as dt
import numpy as np
from rga_etl.pc.rga import set_rga_analog_scan_parameters


def fake_analog_scan():
    """Returns a fake RGA object, mass axis, and spectrum for testing analog scan purposes.

    Returns:
        rga: SimpleNamespace
            A fake RGA object with scan parameters set.
        mass_axis: np.ndarray
            An array of mass/charge values.
        intensities: np.ndarray
            An array of random intensities corresponding to the mass axis.

    """
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga_analog_scan_parameters(rga)
    mass_axis = np.linspace(1, 200, 1991)
    intensities = np.random.rand(len(mass_axis)) * 1e-9
    return rga, mass_axis, intensities


def fake_p_vs_t_scan(started_at, masses, total_time, time_interval):
    """Returns a fake RGA object, times, and intensities for testing pressure vs time scan purposes.

    Args:
        started_at (datetime): The start time of the scan.
        masses (list): List of masses to scan.
        total_time (float): Total duration of the scan in seconds.
        time_interval (float): Time interval between scans in seconds.
    Returns:
        rga: SimpleNamespace
            A fake RGA object with scan parameters set.
        times: np.ndarray
            A 2D array of time points for each mass.
        intensities: np.ndarray
            A 2D array of random intensities for each mass at each time point.

    """
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga_analog_scan_parameters(rga)
    times = []
    intensities = []
    for i in range(math.ceil(total_time / time_interval)):
        _times = []
        _intensities = []
        for mass in masses:
            _times.append((dt.datetime.utcnow() - started_at).total_seconds())
            _intensities.append(np.random.rand() * 1e-9)
        times.append(_times)
        intensities.append(_intensities)
        time.sleep(time_interval)

    times = np.array(times)
    intensities = np.array(intensities)
    return rga, times, intensities
