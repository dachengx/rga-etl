import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from rga_etl.mysql import Instrument


Base = declarative_base()


def mysql_url():
    load_dotenv()
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "rga_user")
    pw = os.getenv("MYSQL_PASSWORD", "rgapw")
    db = os.getenv("MYSQL_DB", "rga")
    return f"mysql+mysqlconnector://{user}:{pw}@{host}:{port}/{db}"


def ensure_schema(engine):
    Base.metadata.create_all(engine)


def init_session():
    engine = create_engine(mysql_url(), pool_pre_ping=True, pool_recycle=3600)
    ensure_schema(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return Session


def init_instrument(session):
    instrument = session.query(Instrument).filter_by(name="RGA200").one_or_none()
    if not instrument:
        instrument = Instrument(name="RGA200", serial="17405")
        session.add(instrument)
        session.commit()
    return instrument
