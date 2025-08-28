import os
from types import SimpleNamespace
import datetime as dt
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError
from srsinst.rga import RGA100


Base = declarative_base()


class Instrument(Base):
    __tablename__ = "instruments"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    serial = Column(String(64))
    executions = relationship(
        "Execution", back_populates="instrument", cascade="all, delete-orphan"
    )


class Execution(Base):
    __tablename__ = "executions"
    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=lambda: dt.datetime.utcnow())
    ended_at = Column(DateTime)
    instrument = relationship("Instrument", back_populates="executions")
    scans = relationship("AnalogScan", back_populates="execution", cascade="all, delete-orphan")

    def end(self):
        self.ended_at = dt.datetime.utcnow()


class AnalogScan(Base):
    __tablename__ = "analog_scans"
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    initial_mass = Column(Float, nullable=False)
    final_mass = Column(Float, nullable=False)
    resolution = Column(Integer, nullable=False)  # points per amu
    scan_speed = Column(Float, nullable=False)
    detector = Column(Enum("FC", "CDEM", name="detector"), nullable=False)
    execution = relationship("Execution", back_populates="scans")
    points = relationship("AnalogScanPoint", back_populates="scan", cascade="all, delete-orphan")


class AnalogScanPoint(Base):
    __tablename__ = "analog_scan_points"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("analog_scans.id", ondelete="CASCADE"), nullable=False)
    amu = Column(Float, nullable=False)
    pressure = Column(Float, nullable=False)
    scan = relationship("AnalogScan", back_populates="points")


def mysql_url_from_env():
    load_dotenv()
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "rga_user")
    pw = os.getenv("MYSQL_PASSWORD", "rgapw")
    db = os.getenv("MYSQL_DB", "rga")
    return f"mysql+mysqlconnector://{user}:{pw}@{host}:{port}/{db}"


def ensure_schema(engine):
    Base.metadata.create_all(engine)


def init_rga():
    usb_serial_device_identifier = "/dev/tty.usbserial-FTEIZFXM"
    baud_rate = 28800

    rga = RGA100("serial", usb_serial_device_identifier, baud_rate)
    return rga


def set_rga(rga):
    rga.scan.initial_mass = 1
    rga.scan.final_mass = 200
    rga.scan.resolution = 10
    rga.scan.scan_speed = 3
    return rga


def fake_analog_scan():
    rga = SimpleNamespace(scan=SimpleNamespace())
    set_rga(rga)
    mass_axis = np.linspace(1, 200, 1991)
    spectrum = np.random.rand(len(mass_axis)) * 1e-9
    return rga, mass_axis, spectrum


def analog_scan(session, execution: Execution):
    load_dotenv()
    fake = os.getenv("FAKE_ANALOG_SCAN", "0") == "1"
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
    engine = create_engine(mysql_url_from_env(), pool_pre_ping=True, pool_recycle=3600)
    ensure_schema(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with Session() as session:
        instrument = session.query(Instrument).filter_by(name="RGA200").one_or_none()
        if not instrument:
            instrument = Instrument(name="RGA200", serial="17405")
            session.add(instrument)
            session.commit()
        execution = Execution(instrument_id=instrument.id)
        session.add(execution)
        session.flush()
        analog_scan(session, execution)
        execution.end()
        session.commit()


if __name__ == "__main__":
    main()
