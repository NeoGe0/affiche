import logging
import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from affiche.config.env_config import DB_DIR

DB_PATH = Path(DB_DIR)
DB_PATH.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_DIR}/affiche.db")

IS_SQLITE = "sqlite" in DATABASE_URL

POOL_SIZE = 20
MAX_OVERFLOW = 40

POOL_TIMEOUT_SECONDS = 10

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT_SECONDS,
    pool_pre_ping=not IS_SQLITE,
)

def apply_sqlite_pragmas(dbapi_connection) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        apply_sqlite_pragmas(dbapi_connection)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def database_ok() -> bool:
    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("Database health check failed", exc_info=True)
        return False
    finally:
        if db is not None:
            db.close()

def init_db():

    from alembic.config import Config
    from alembic import command
    from pathlib import Path

    try:
        project_root = Path(__file__).parent.parent.parent
        alembic_ini_path = project_root / "alembic.ini"
        alembic_dir = Path(__file__).parent.parent / "alembic"

        if not alembic_ini_path.exists():
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")

        if not alembic_dir.exists():
            raise FileNotFoundError(f"alembic directory not found at {alembic_dir}")

        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(alembic_dir))

        command.upgrade(alembic_cfg, "head")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
