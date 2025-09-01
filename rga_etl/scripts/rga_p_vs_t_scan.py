import os
import argparse
import time
import math
import datetime as dt
import numpy as np
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from rga_etl.utils import init_session, init_instrument
from rga_etl.rga import init_rga, set_rga_parameters_to_execution, rga_turn_off_filament
from rga_etl.mysql import Execution, PvsTScan, PvsTScanPoint
from rga_etl.fake import fake_p_vs_t_scan


def p_vs_t_scan(session, masses):
    """Performs a pressure vs time scan for the specified masses
    and records the data in the database.
    Args:
        session: SQLAlchemy session object.
        masses (list): List of masses to scan.
    """
    load_dotenv()
    total_time = float(os.getenv("RGA_SCAN_TOTAL_TIME", "60"))
    time_interval = float(os.getenv("RGA_SCAN_TIME_INTERVAL", "5"))
    fake = os.getenv("FAKE_EXECUTION", "0") == "1"

    instrument = init_instrument(session)

    execution = Execution(
        instrument_id=instrument.id,
        _fake_execution=fake,
    )
    session.add(execution)
    session.flush()

    if fake:
        started_at = dt.datetime.utcnow()
        rga, times, intensities = fake_p_vs_t_scan(started_at, masses, total_time, time_interval)
        ended_at = dt.datetime.utcnow()
        masses = np.repeat([masses], len(times), axis=0)
    else:
        rga = init_rga()
        rga.filament.turn_on()

        set_rga_parameters_to_execution(rga, execution)

        started_at = dt.datetime.utcnow()
        times = []
        intensities = []
        for i in range(math.ceil(total_time / time_interval)):
            _times = np.full(len(masses), (dt.datetime.utcnow() - started_at).total_seconds())
            _intensities = rga.scan.get_multiple_mass_scan(masses)
            times.append(_times)
            intensities.append(_intensities)
            time.sleep(time_interval)
        ended_at = dt.datetime.utcnow()
        masses = np.repeat([masses], len(times), axis=0)
        times = np.array(times)
        intensities = np.array(intensities)
        rga.filament.turn_off()

    scan = PvsTScan(
        execution_id=execution.id,
        started_at=started_at,
        ended_at=ended_at,
        total_time=total_time,
        time_interval=time_interval,
    )
    session.add(scan)
    session.flush()  # get scan.id

    session.bulk_save_objects(
        [
            PvsTScanPoint(scan_id=scan.id, mass=m, time=t, intensity=i)
            for m, t, i in zip(masses.flatten(), times.flatten(), intensities.flatten())
        ]
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()

    execution.end()
    session.commit()


def main():
    parser = argparse.ArgumentParser(description="Pressure vs time scan of one or multiple masses")
    parser.add_argument(
        "--masses",
        type=float,
        nargs="+",
        help="List of float masses in amu to scan",
        required=False,
    )
    args = parser.parse_args()
    Session = init_session()
    with Session() as session:
        if args.masses is not None:
            masses = args.masses
        elif os.getenv("RGA_MASSES") is not None:
            masses = [float(f) for f in os.getenv("RGA_MASSES").replace(" ", "").split(",")]
        else:
            raise ValueError("No masses provided for pressure vs time scan")
        try:
            p_vs_t_scan(session, masses)
        except Exception as e:
            rga_turn_off_filament()
            raise e


if __name__ == "__main__":
    main()
