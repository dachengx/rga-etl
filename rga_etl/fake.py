import time
import math
from types import SimpleNamespace
import datetime as dt
import numpy as np
from rga_etl.rga import set_rga


def fake_analog_scan():
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga(rga)
    mass_axis = np.linspace(1, 200, 1991)
    spectrum = np.random.rand(len(mass_axis)) * 1e-9
    return rga, mass_axis, spectrum


def fake_p_vs_t_scan(started_at, masses, total_time, time_interval):
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga(rga)
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
