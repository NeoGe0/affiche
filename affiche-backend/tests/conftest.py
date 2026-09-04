import os
import shutil
import tempfile

_TEST_STATE_DIR = tempfile.mkdtemp(prefix="affiche-tests-")
os.environ["CONFIG_DIR"] = _TEST_STATE_DIR
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_STATE_DIR}/test.db"

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from affiche.config import Base

def pytest_configure(config):
    from affiche.config.database import DATABASE_URL
    from affiche.config.env_config import DB_DIR, FILESTORE_DIR

    for label, value in (
        ("DATABASE_URL", DATABASE_URL),
        ("DB_DIR", DB_DIR),
        ("FILESTORE_DIR", FILESTORE_DIR),
    ):
        assert _TEST_STATE_DIR in str(value), (
            f"{label} resolved to {value!r}, outside the test sandbox {_TEST_STATE_DIR!r}. "
            "An `affiche` module was imported before conftest set the environment; tests would "
            "write to real data. Fix the import order rather than relaxing this check."
        )

def pytest_unconfigure(config):
    shutil.rmtree(_TEST_STATE_DIR, ignore_errors=True)

@pytest.fixture
def authenticated_app():
    from affiche.app.auth.model.user import User
    from affiche.config.dependencies import get_current_user
    from affiche.main import app

    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, username="test-admin", password_hash="not-a-real-hash"
    )
    yield app
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def session(engine) -> Session:
    connection = engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def clean_session(engine) -> Session:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()

    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
