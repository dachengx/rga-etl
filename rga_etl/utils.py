import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rga_etl.mysql import Instrument, ensure_schema


def mysql_url():
    load_dotenv()
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "rga_user")
    pw = os.getenv("MYSQL_PASSWORD", "rgapw")
    db = os.getenv("MYSQL_DB", "rga")
    return f"mysql+mysqlconnector://{user}:{pw}@{host}:{port}/{db}"


def init_session():
    engine = create_engine(mysql_url(), pool_pre_ping=True, pool_recycle=3600)
    ensure_schema(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return Session


def init_instrument(session):
    load_dotenv()
    name = os.getenv("RGA_MODEL", "RGA200")
    instrument = session.query(Instrument).filter_by(name=name).one_or_none()
    if not instrument:
        serial = os.getenv("RGA_SERIAL_NUMBER", "17405")
        instrument = Instrument(name=name, serial=serial)
        session.add(instrument)
        session.commit()
    return instrument
