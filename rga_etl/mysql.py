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
    analog_scans = relationship(
        "AnalogScan", back_populates="execution", cascade="all, delete-orphan"
    )
    p_vs_t_scans = relationship(
        "PvsTScan", back_populates="execution", cascade="all, delete-orphan"
    )

    def end(self):
        self.ended_at = dt.datetime.utcnow()


class AnalogScan(Base):
    __tablename__ = "analog_scans"
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    initial_mass = Column(Float, nullable=False)
    final_mass = Column(Float, nullable=False)
    resolution = Column(Integer, nullable=False)  # points per amu
    scan_speed = Column(Float, nullable=False)
    detector = Column(Enum("FC", "CDEM", name="detector"), nullable=False)
    execution = relationship("Execution", back_populates="analog_scans")
    points = relationship("AnalogScanPoint", back_populates="scan", cascade="all, delete-orphan")


class AnalogScanPoint(Base):
    __tablename__ = "analog_scan_points"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("analog_scans.id", ondelete="CASCADE"), nullable=False)
    amu = Column(Float, nullable=False)
    pressure = Column(Float, nullable=False)
    scan = relationship("AnalogScan", back_populates="points")


class PvsTScan(Base):
    __tablename__ = "p_vs_t_scans"
    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    detector = Column(Enum("FC", "CDEM", name="detector"), nullable=False)
    execution = relationship("Execution", back_populates="p_vs_t_scans")
    points = relationship("PvsTScanPoint", back_populates="scan", cascade="all, delete-orphan")


class PvsTScanPoint(Base):
    __tablename__ = "p_vs_t_scan_points"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("p_vs_t_scans.id", ondelete="CASCADE"), nullable=False)
    mass = Column(Float, nullable=False)  # amu
    time = Column(Float, nullable=False)  # seconds since start of scan
    intensity = Column(Float, nullable=False)
    scan = relationship("PvsTScan", back_populates="points")


def ensure_schema(engine):
    Base.metadata.create_all(engine)
