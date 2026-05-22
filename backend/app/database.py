import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://saltim:saltim123@localhost:5432/saltim_db")
SQL_LOADER_FILES = ("load_data_csvs.sql", "load_ml_dataset.sql")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _csv_loader_enabled() -> bool:
    value = os.getenv("LOAD_CSV_DATA_ON_STARTUP", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def run_sql_loaders() -> None:
    if not _csv_loader_enabled():
        return

    sql_dir = Path(__file__).resolve().parents[1] / "db"
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            for filename in SQL_LOADER_FILES:
                script_path = sql_dir / filename
                cursor.execute(script_path.read_text(encoding="utf-8"))
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()
