import os
import datetime as dt
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from rga_etl.utils import init_session, init_instrument
from rga_etl.rga import init_rga, set_rga
from rga_etl.mysql import Execution, SingleMassScan, SingleMassScanPoint
from rga_etl.fake import fake_single_mass_scan


def single_mass_scan(session, execution: Execution):
    mass = 28
    load_dotenv()
    fake = os.getenv("FAKE_EXECUTION", "0") == "1"
    if fake:
        rga, time, intensity = fake_single_mass_scan(mass)
        started_at = dt.datetime.utcnow()
    else:
        rga = init_rga()
        rga.filament.turn_on()
        set_rga(rga)
        started_at = dt.datetime.utcnow()
        intensity = rga.scan.get_single_scan(mass)
        rga.filament.turn_off()

    scan = SingleMassScan(
        execution_id=execution.id,
        started_at=started_at,
        mass=mass,
        detector="FC",
    )
    session.add(scan)
    session.flush()  # get scan.id

    session.bulk_save_objects(
        [SingleMassScanPoint(scan_id=scan.id, time=t, intensity=i) for t, i in zip(time, intensity)]
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
        single_mass_scan(session, execution)
        execution.end()
        session.commit()


if __name__ == "__main__":
    main()
