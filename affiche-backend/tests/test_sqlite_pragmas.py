from sqlalchemy import create_engine, event, text

from affiche.config.database import apply_sqlite_pragmas

def test_pragmas_applied_on_connect(tmp_path):
    db_file = tmp_path / "pragmas.db"
    engine = create_engine(f"sqlite:///{db_file}")

    @event.listens_for(engine, "connect")
    def _connect(dbapi_connection, connection_record):
        apply_sqlite_pragmas(dbapi_connection)

    try:
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA journal_mode")).scalar().lower() == "wal"
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
    finally:
        engine.dispose()
