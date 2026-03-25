import json
import logging
import datetime as dt

import numpy as np
from sqlalchemy.exc import IntegrityError

from rga_etl.databases.utils import init_session, init_instrument
from rga_etl.databases.mysql import Execution, AnalogScan, AnalogScanPoint
from rga_etl.pc_plc.http_handlers.shared import (
    INIT_COMMANDS,
    END_COMMANDS,
    PARAM_COMMANDS,
    fill_execution_params,
)


def handle_analog_scan(req, data, publish, subscribe):
    try:
        initial_mass = int(data["INITIAL_MASS"])
        final_mass = int(data["FINAL_MASS"])
        scan_rate = int(data["SCAN_RATE"])
        steps_per_amu = int(data["STEPS_PER_AMU"])
        if not (1 <= initial_mass < final_mass):
            raise ValueError(
                "INITIAL_MASS must be < FINAL_MASS and >= 1 "
                f"(got INITIAL_MASS={initial_mass}, FINAL_MASS={final_mass})"
            )
        if not (0 <= scan_rate <= 7):
            raise ValueError(f"SCAN_RATE must be between 0 and 7 (got {scan_rate})")
        if not (10 <= steps_per_amu <= 25):
            raise ValueError(f"STEPS_PER_AMU must be between 10 and 25 (got {steps_per_amu})")
    except (KeyError, ValueError) as e:
        req._reject(400, str(e))
        return

    # There is a last byte in the response of SC command that indicates the total pressure
    n = (final_mass - initial_mass) * steps_per_amu + 1
    logging.info(f"Analog scan: n={n} data points")
    commands = [
        {"rga/main": f"MI{initial_mass}\r", "rga/length": 128, "noresult": 1, "timeout": 1.0},
        {"rga/main": f"MF{final_mass}\r", "rga/length": 128, "noresult": 1, "timeout": 1.0},
        {"rga/main": f"NF{scan_rate}\r", "rga/length": 128, "noresult": 1, "timeout": 1.0},
        {"rga/main": f"SA{steps_per_amu}\r", "rga/length": 128, "noresult": 1, "timeout": 1.0},
        {"rga/main": "AP?\r", "rga/length": 128, "noresult": 0, "timeout": 1.0},
        {"rga/main": "SC1\r", "rga/length": (n + 1) * 4, "noresult": 0, "timeout": 10.0},
    ]

    try:
        req._run_commands(INIT_COMMANDS, publish, subscribe)
        param_results = req._run_commands(PARAM_COMMANDS, publish, subscribe)

        started_at = dt.datetime.utcnow()
        results = req._run_commands(commands, publish, subscribe)
        ended_at = dt.datetime.utcnow()
        req._run_commands(END_COMMANDS, publish, subscribe)
    except TimeoutError as e:
        req._reject(500, str(e))
        return

    # results[4] = AP? (expected number of data points)
    # results[5] = SC1 (intensities, last element is total pressure)
    ap_n = results[4]
    if ap_n != n:
        req._reject(500, f"AP? returned {ap_n} data points, expected {n}")
        return

    sc_len = len(results[5])
    if sc_len != n + 1:
        req._reject(500, f"SC1 returned {sc_len} values, expected {n + 1}")
        return

    intensities = results[5][:-1]
    total_pressure = results[5][-1]
    step = 1.0 / steps_per_amu
    # Mirrors: Scans.get_mass_axis() in srsinst.rga, which also uses np.arange.
    mass_axis = np.arange(initial_mass, final_mass + step / 2.0, step)

    Session = init_session()
    with Session() as session:
        instrument = init_instrument(session)
        execution = Execution(instrument_id=instrument.id)
        fill_execution_params(execution, param_results)
        session.add(execution)
        session.flush()

        scan = AnalogScan(
            execution_id=execution.id,
            started_at=started_at,
            ended_at=ended_at,
            initial_mass=initial_mass,
            final_mass=final_mass,
            resolution=steps_per_amu,
            scan_speed=scan_rate,
        )
        session.add(scan)
        session.flush()

        session.bulk_save_objects(
            [
                AnalogScanPoint(scan_id=scan.id, amu=float(a), intensity=float(i))
                for a, i in zip(mass_axis, intensities)
            ]
        )
        execution.end()
        try:
            session.commit()
        except IntegrityError:
            session.rollback()

    req._set_headers(200)
    req.wfile.write(
        json.dumps(
            {
                "status": "ok",
                "initial_mass": initial_mass,
                "final_mass": final_mass,
                "n": n,
                "total_pressure": total_pressure,
                "intensities": intensities,
            }
        ).encode()
    )
