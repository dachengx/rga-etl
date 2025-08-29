import numpy as np
from types import SimpleNamespace
from rga_etl.rga import set_rga


def fake_analog_scan():
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga(rga)
    mass_axis = np.linspace(1, 200, 1991)
    spectrum = np.random.rand(len(mass_axis)) * 1e-9
    return rga, mass_axis, spectrum


def fake_single_mass_scan(mass):
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga(rga)
    raise NotImplementedError
    # return rga, intensity


def fake_p_vs_t(masses):
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga(rga)
    raise NotImplementedError
    # return rga, intensities
