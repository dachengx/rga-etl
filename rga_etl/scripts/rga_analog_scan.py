import os
import datetime as dt
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from rga_etl.utils import init_session, init_instrument
from rga_etl.rga import init_rga, set_rga
from rga_etl.mysql import Execution, AnalogScan, AnalogScanPoint
from rga_etl.fake import fake_analog_scan


def analog_scan(session, execution: Execution):
    load_dotenv()
    fake = os.getenv("FAKE_EXECUTION", "0") == "1"
    if fake:
        rga, analog_mass_axis, spectrum_in_torr = fake_analog_scan()
        started_at = dt.datetime.utcnow()
    else:
        rga = init_rga()
        rga.filament.turn_on()
        set_rga(rga)
        started_at = dt.datetime.utcnow()
        analog_spectrum = rga.scan.get_analog_scan()
        analog_mass_axis = rga.scan.get_mass_axis(True)
        spectrum_in_torr = rga.scan.get_partial_pressure_corrected_spectrum(analog_spectrum)
        rga.filament.turn_off()

    scan = AnalogScan(
        execution_id=execution.id,
        started_at=started_at,
        initial_mass=rga.scan.initial_mass,
        final_mass=rga.scan.final_mass,
        resolution=rga.scan.resolution,
        scan_speed=rga.scan.scan_speed,
        detector="FC",
    )
    session.add(scan)
    session.flush()  # get scan.id

    session.bulk_save_objects(
        [
            AnalogScanPoint(scan_id=scan.id, amu=a, pressure=p)
            for a, p in zip(analog_mass_axis, spectrum_in_torr)
        ]
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


def main():
    Session = init_session()
    with Session() as session:
        instrument = init_instrument(session)
        execution = Execution(instrument_id=instrument.id)
        session.add(execution)
        session.flush()
        analog_scan(session, execution)
        execution.end()
        session.commit()


if __name__ == "__main__":
    main()
