import datetime as dt
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Instrument(Base):
    """SQLAlchemy model for an RGA instrument."""

    __tablename__ = "instruments"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    serial = Column(String(64))
    executions = relationship(
        "Execution", back_populates="instrument", cascade="all, delete-orphan"
    )


class Execution(Base):
    """SQLAlchemy model for an execution of scans on an RGA instrument."""

    __tablename__ = "executions"
    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)

    started_at = Column(DateTime, nullable=False, default=lambda: dt.datetime.utcnow())
    ended_at = Column(DateTime)
    detector = Column(Enum("FC", "CDEM", name="detector"), nullable=True)
    # detector settings are nullable because they will be set after initialization
    electron_energy = Column(Float, nullable=True)
    ion_energy = Column(Float, nullable=True)
    focus_voltage = Column(Float, nullable=True)
    emission_current = Column(Float, nullable=True)
    # CDEM related fields are not detailed yet
    cdem_stored_voltage = Column(Float, nullable=True)
    cdem_stored_gain = Column(Float, nullable=True)
    cdem_voltage = Column(Float, nullable=True)
    total_pressure = Column(Float, nullable=False)  # in Torr
    partial_pressure_sensitivity_factor = Column(Float, nullable=False)  # in 0.1 fA / Torr
    # indicates if the execution was performed in fake mode for testing
    _fake_execution = Column("fake_execution", Integer, nullable=False, default=0)

    instrument = relationship("Instrument", back_populates="executions")
    analog_scans = relationship(
        "AnalogScan", back_populates="execution", cascade="all, delete-orphan"
    )
    p_vs_t_scans = relationship(
        "PvsTScan", back_populates="execution", cascade="all, delete-orphan"
    )

    def end(self):
        self.ended_at = dt.datetime.utcnow()


class AnalogScan(Base):
    """SQLAlchemy model for an analog scan performed during an execution."""

    __tablename__ = "analog_scans"
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)

    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    initial_mass = Column(Float, nullable=False)
    final_mass = Column(Float, nullable=False)
    resolution = Column(Integer, nullable=False)  # points per amu
    scan_speed = Column(Float, nullable=False)

    execution = relationship("Execution", back_populates="analog_scans")
    points = relationship("AnalogScanPoint", back_populates="scan", cascade="all, delete-orphan")


class AnalogScanPoint(Base):
    """SQLAlchemy model for a data point in an analog scan."""

    __tablename__ = "analog_scan_points"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("analog_scans.id", ondelete="CASCADE"), nullable=False)

    amu = Column(Float, nullable=False)
    intensity = Column(Float, nullable=False)  # in 0.1 fA

    scan = relationship("AnalogScan", back_populates="points")


class PvsTScan(Base):
    """SQLAlchemy model for a pressure vs time scan performed during an execution."""

    __tablename__ = "p_vs_t_scans"
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)

    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    total_time = Column(Float, nullable=False)  # seconds
    time_interval = Column(Float, nullable=False)  # seconds between points

    execution = relationship("Execution", back_populates="p_vs_t_scans")
    points = relationship("PvsTScanPoint", back_populates="scan", cascade="all, delete-orphan")


class PvsTScanPoint(Base):
    """SQLAlchemy model for a data point in a pressure vs time scan."""

    __tablename__ = "p_vs_t_scan_points"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("p_vs_t_scans.id", ondelete="CASCADE"), nullable=False)

    mass = Column(Float, nullable=False)  # amu
    time = Column(Float, nullable=False)  # seconds since start of scan
    intensity = Column(Float, nullable=False)  # in 0.1 fA

    scan = relationship("PvsTScan", back_populates="points")


def ensure_schema(engine):
    """Ensure that the database schema is created."""
    Base.metadata.create_all(engine)
