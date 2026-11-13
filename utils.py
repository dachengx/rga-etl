import re
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import trapezoid
from scipy.ndimage import median_filter


def read_rga_file(filename):
    masses = None
    data_start_line = None

    with open(filename, "r") as f:
        for line_number, line in enumerate(f):
            if "Elapsed Time (s)" in line:
                masses = [int(x) for x in re.findall(r"Mass\s+(\d+)", line)]
                data_start_line = line_number + 1
                break

    if masses is None:
        raise ValueError("Could not find data header.")

    data = np.loadtxt(filename, delimiter=",", skiprows=data_start_line)

    if data.ndim == 1:
        data = data[np.newaxis, :]

    if data.shape[1] != len(masses) + 1:
        raise ValueError("Number of columns does not match number of masses.")

    result = {"t": data[:, 0]}

    for i, mass in enumerate(masses):
        result[mass] = data[:, i + 1]

    return result


def get_t0(
    x,
    y,
    slope_window=7,
    slope_fraction=0.05,
    min_rise_dex=0.05,
    max_gap=2,
    baseline_points=8,
    onset_fraction=0.05,
    t0_range=(8 * 60, 13 * 60),
    debug=False,
):
    x = np.asarray(x)
    y = np.asarray(y)

    mask = np.isfinite(x) & np.isfinite(y) & (y > 0)
    x = x[mask]
    y = y[mask]

    order = np.argsort(x)
    x = x[order]
    y = y[order]

    z = median_filter(np.log10(y), size=3, mode="nearest")

    n = len(x)

    if slope_window % 2 == 0:
        slope_window += 1

    h = slope_window // 2

    slope = np.full(n, np.nan)

    for i in range(h, n - h):
        xx = x[i - h : i + h + 1]
        zz = z[i - h : i + h + 1]

        xm = np.mean(xx)

        slope[i] = np.sum((xx - xm) * (zz - np.mean(zz))) / np.sum((xx - xm) ** 2)

    in_window = (x >= t0_range[0]) & (x <= t0_range[1])

    if not np.any(in_window):
        raise ValueError(f"No data in {t0_range} s.")

    imax = np.flatnonzero(in_window)[np.argmax(z[in_window])]

    valid_slope = slope[h:imax]

    median_slope = np.nanmedian(valid_slope)

    slope_noise = 1.4826 * np.nanmedian(np.abs(valid_slope - median_slope))

    max_slope = np.nanmax(valid_slope)

    slope_threshold = max(
        5.0 * slope_noise,
        slope_fraction * max_slope,
    )

    active = slope > slope_threshold
    active[imax:] = False

    indices = np.where(active)[0]

    if len(indices) == 0:
        raise ValueError("No significant rising region found.")

    runs = []

    start = indices[0]
    previous = indices[0]

    for i in indices[1:]:
        if i - previous <= max_gap + 1:
            previous = i
        else:
            runs.append((start, previous))
            start = i
            previous = i

    runs.append((start, previous))

    good_runs = []

    for start, end in runs:
        i1 = max(0, start - h)
        i2 = min(imax, end + h)

        rise = z[i2] - z[i1]

        in_range = (x[end] >= t0_range[0]) & (x[start] <= t0_range[1])

        if rise >= min_rise_dex and in_range:
            good_runs.append((start, end))

    if len(good_runs) == 0:
        raise ValueError(f"No significant sustained rise found in {t0_range} s.")

    rise_start, rise_end = good_runs[-1]

    b1 = max(0, rise_start - baseline_points)
    b2 = max(b1 + 1, rise_start - 1)

    baseline = np.median(z[b1:b2])
    peak = z[imax]

    target = baseline + onset_fraction * (peak - baseline)

    search_start = max(0, rise_start - h - 3)

    crossing = np.where(
        (z[search_start:imax] <= target) & (z[search_start + 1 : imax + 1] > target)
    )[0]

    if len(crossing) == 0:
        t0 = x[rise_start]
    else:
        i = search_start + crossing[0]

        t0 = x[i] + (target - z[i]) * (x[i + 1] - x[i]) / (z[i + 1] - z[i])

    if not t0_range[0] <= t0 <= t0_range[1]:
        raise ValueError(f"t0 = {t0:.1f} s is outside {t0_range} s.")

    if debug:
        plt.figure()

        plt.semilogy(x, y)
        plt.axvline(t0, ls="--", label=f"t0 = {t0:.1f} s")
        plt.axvline(x[imax], ls=":", label="maximum")

        plt.xlabel("Time [s]")
        plt.ylabel("Partial Pressure [Torr]")
        plt.legend()
        plt.tight_layout()
        plt.show()

    return t0


def get_integral(x, y, xmin=5, xmax=250):
    mask = (x > xmin) & (x < xmax)

    xx = np.r_[xmin, x[mask], xmax]
    yy = np.interp(xx, x, y)

    integral = trapezoid(yy, xx)
    return integral


def get_partial_pressure(
    rga,
    t0,
    mass=84,
    ref=87,
    bkg_window=(-300, 0),
    flw_window=(5, 250),
):
    """Sample partial pressure P_sample(A) and its standard uncertainty.

    Follows Sec. 1 of notes/202611.tex without the low- or high-concentration
    approximations: sigma_k(A) = sigma_0 [1 + c dp_k(A)] is summed over every
    measurement group of both runs.

    Args:
        rga: dict from read_rga_file.
        t0: start of the flow run [s], e.g. from get_t0.
        mass: AMU of interest, A in the note.
        ref: AMU of the empty reference channel.
        bkg_window: background run (t_min, t_max) relative to t0 [s].
        flw_window: flow run (t_min, t_max) relative to t0 [s].

    Returns:
        P_sample, P_sample_err: in Torr.

    """
    t = rga["t"] - t0
    mask_bkg = (t > bkg_window[0]) & (t < bkg_window[1])
    mask_flw = (t > flw_window[0]) & (t < flw_window[1])

    # Reference-subtracted partial pressures dp_k(A) = p_k(A) - p_k(ref)
    dp_bkg = rga[mass][mask_bkg] - rga[ref][mask_bkg]
    dp_flw = rga[mass][mask_flw] - rga[ref][mask_flw]

    P_bkg = dp_bkg.mean()
    P_flw = dp_flw.mean()

    # sigma_0 of each run from the reference channel, c from the background run
    sigma_0_bkg = np.std(rga[ref][mask_bkg], ddof=1)
    sigma_0_flw = np.std(rga[ref][mask_flw], ddof=1)
    sigma_bkg = np.std(rga[mass][mask_bkg], ddof=1)
    c = (sigma_bkg / sigma_0_bkg - 1) / P_bkg

    # Variance of each run average, including the reference channel
    def var_mean(dp, sigma_0):
        N = len(dp)
        return np.sum((sigma_0 * (1 + c * dp)) ** 2) / N**2 + sigma_0**2 / N

    P_sample = P_flw - P_bkg
    P_sample_err = np.sqrt(var_mean(dp_flw, sigma_0_flw) + var_mean(dp_bkg, sigma_0_bkg))

    return P_sample, P_sample_err


# Constants of the krypton calibration, see Sec. 2 of notes/202611.tex
TORR = 133.322368  # Pa
R_GAS = 8.314462618  # J/(mol K)
M_XE = 131.293e-3  # kg/mol, CIAAW
EPSILON = 10  # V/Torr, pressure transducer sensitivity
P_BETA_1 = 0.9965 + 0.012  # pressure reading in beta_1
P_BETA_12 = 0.0016 + 0.012  # pressure reading in beta_1 + beta_2
P_REL_ERR = 0.0025  # relative uncertainty of each corrected pressure reading
BETA_2, BETA_2_ERR = 620e-6, 21e-6  # m^3, CAD
BETA_3, BETA_3_ERR = 1107e-6, 44e-6  # m^3, recycler
EOS_REL_ERR = 0.001  # Lemmon and Span, k=1


def get_kr_concentration(
    delta_v=0.0842,
    n_expansion=2,
    temperature=292,
    recycler_pressure=14.8,
    delta_temperature=3,
):
    """Krypton mole fraction in xenon and its standard uncertainty.

    Follows Sec. 2 of notes/202611.tex, generalized to n_expansion expansions.
    After the last expansion, the gas near PT1 is pumped and the gas near PTq
    is expanded into the infuser, contributing a further factor 1 / (1 + R).

    Args:
        delta_v: transducer voltage difference before the first expansion [V].
        n_expansion: number of expansions, each retaining the fraction R in beta_1.
        temperature: temperature of both krypton and xenon [K].
        recycler_pressure: absolute xenon pressure in the recycler [bar].
        delta_temperature: standard uncertainty of each of the two temperatures [K].

    Returns:
        x_kr, x_kr_err: mole fraction and its standard uncertainty.

    """
    # Imported here so that the rest of utils works without CoolProp
    from CoolProp.CoolProp import PropsSI

    # Volume fraction R = beta_1 / (beta_1 + beta_2) and calibrated beta_1
    R = P_BETA_12 / P_BETA_1
    R_rel_err = np.sqrt(2) * P_REL_ERR
    beta_1 = BETA_2 * R / (1 - R)

    # Krypton amount delivered to the infuser, n_Kr ∝ R^(n + 1) / (1 - R^2)
    p_kr_0 = delta_v / EPSILON * TORR
    n_kr = R**n_expansion / (1 + R) * p_kr_0 * beta_1 / (R_GAS * temperature)
    n_kr_rel_err = np.sqrt(
        P_REL_ERR**2
        + (delta_temperature / temperature) ** 2
        + (BETA_2_ERR / BETA_2) ** 2
        + ((n_expansion + 1 + 2 * R**2 / (1 - R**2)) * R_rel_err) ** 2
    )

    # Xenon amount in the recycler from the Lemmon and Span equation of state
    p = recycler_pressure * 1e5
    rho_xe = PropsSI("Dmass", "T", temperature, "P", p, "HEOS::Xenon")
    drho_dT = PropsSI("d(Dmass)/d(T)|P", "T", temperature, "P", p, "HEOS::Xenon")
    n_xe = rho_xe * BETA_3 / M_XE
    n_xe_rel_err = np.sqrt(
        (BETA_3_ERR / BETA_3) ** 2
        + EOS_REL_ERR**2
        + (abs(drho_dT) * delta_temperature / rho_xe) ** 2
    )

    # Mole fraction, krypton and xenon amounts independent
    x_kr = n_kr / (n_kr + n_xe)
    x_kr_rel_err = (1 - x_kr) * np.sqrt(n_kr_rel_err**2 + n_xe_rel_err**2)

    return x_kr, x_kr_rel_err * x_kr
