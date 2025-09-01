import os
import datetime as dt
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from rga_etl.utils import init_session, init_instrument
from rga_etl.rga import (
    init_rga,
    set_rga_analog_scan_parameters,
    set_rga_parameters_to_execution,
    rga_turn_off_filament,
)
from rga_etl.mysql import Execution, AnalogScan, AnalogScanPoint
from rga_etl.fake import fake_analog_scan


def analog_scan(session):
    """Performs an analog scan and records the data in the database.
    Args:
        session: SQLAlchemy session object.
    """
    load_dotenv()
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
        rga, analog_mass_axis, analog_spectrum = fake_analog_scan()
        ended_at = dt.datetime.utcnow()
    else:
        rga = init_rga()
        rga.filament.turn_on()

        set_rga_parameters_to_execution(rga, execution)

        set_rga_analog_scan_parameters(rga)
        started_at = dt.datetime.utcnow()
        analog_spectrum = rga.scan.get_analog_scan()
        ended_at = dt.datetime.utcnow()
        rga.filament.turn_off()

        analog_mass_axis = rga.scan.get_mass_axis(True)

    scan = AnalogScan(
        execution_id=execution.id,
        started_at=started_at,
        ended_at=ended_at,
        initial_mass=rga.scan.initial_mass,
        final_mass=rga.scan.final_mass,
        resolution=rga.scan.resolution,
        scan_speed=rga.scan.scan_speed,
    )
    session.add(scan)
    session.flush()  # get scan.id

    session.bulk_save_objects(
        [
            AnalogScanPoint(scan_id=scan.id, amu=a, intensity=i)
            for a, i in zip(analog_mass_axis, analog_spectrum)
        ]
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()

    execution.end()
    session.commit()


def main():
    Session = init_session()
    with Session() as session:
        try:
            analog_scan(session)
        except Exception as e:
            rga_turn_off_filament()
            raise e


if __name__ == "__main__":
    main()
