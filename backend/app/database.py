import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://saltim:saltim123@localhost:5432/saltim_db")
DATA_LOADER_FILE = "load_data_csvs.sql"
ML_LOADER_FILE = "load_ml_dataset.sql"

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


def _force_csv_reload() -> bool:
    value = os.getenv("FORCE_CSV_DATA_RELOAD", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _seed_data_loaded(cursor) -> bool:
    cursor.execute("SELECT to_regclass('public.categorias')")
    if cursor.fetchone()[0] is None:
        return False

    cursor.execute("SELECT EXISTS (SELECT 1 FROM categorias LIMIT 1)")
    return bool(cursor.fetchone()[0])


def run_sql_loaders() -> None:
    if not _csv_loader_enabled():
        return

    sql_dir = Path(__file__).resolve().parents[1] / "db"
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            if _force_csv_reload() or not _seed_data_loaded(cursor):
                script_path = sql_dir / DATA_LOADER_FILE
                cursor.execute(script_path.read_text(encoding="utf-8"))

            script_path = sql_dir / ML_LOADER_FILE
            cursor.execute(script_path.read_text(encoding="utf-8"))
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()
