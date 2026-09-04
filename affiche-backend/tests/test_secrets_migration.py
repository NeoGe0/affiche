from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from affiche.config import Base
from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity  # noqa: F401
from affiche.app.service_configuration.connector.service_configuration_entity import (  # noqa: F401
    ServiceConfigurationEntity,
)
from affiche.config.env_config import LEGACY_ENCRYPTION_KEY
from affiche.config.secrets_migration import reencrypt_legacy_secrets

_LEGACY = Fernet(LEGACY_ENCRYPTION_KEY.encode())

@pytest.fixture
def migration_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr("affiche.config.secrets_migration.SessionLocal", sessionmaker(bind=engine))

    current_key = Fernet.generate_key()
    monkeypatch.setattr(
        "affiche.config.secrets_migration.get_encryption_key", lambda: current_key
    )
    return engine, Fernet(current_key)

def _insert_media_server(engine, ciphertext: str, name: str = "plex") -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO media_server (name, type, url, token, enabled, "
                "webhook_enabled, created_at, updated_at) "
                "VALUES (:name, 'PLEX', 'http://x', :token, 1, 0, :now, :now)"
            ),
            {"name": name, "token": ciphertext, "now": datetime.now(timezone.utc)},
        )

def _stored_token(engine, name: str = "plex") -> str:
    with engine.begin() as conn:
        return conn.execute(
            text("SELECT token FROM media_server WHERE name = :name"), {"name": name}
        ).scalar_one()

def test_legacy_token_is_reencrypted_with_the_current_key(migration_db):
    engine, current = migration_db
    _insert_media_server(engine, _LEGACY.encrypt(b"plex-token-42").decode())

    assert reencrypt_legacy_secrets() == 1
    assert current.decrypt(_stored_token(engine).encode()) == b"plex-token-42"

def test_migration_is_idempotent(migration_db):
    engine, _ = migration_db
    _insert_media_server(engine, _LEGACY.encrypt(b"plex-token-42").decode())

    assert reencrypt_legacy_secrets() == 1
    assert reencrypt_legacy_secrets() == 0

def test_already_current_tokens_are_left_alone(migration_db):
    engine, current = migration_db
    ciphertext = current.encrypt(b"already-fine").decode()
    _insert_media_server(engine, ciphertext)

    assert reencrypt_legacy_secrets() == 0
    assert _stored_token(engine) == ciphertext

def test_token_from_a_third_key_is_preserved_not_clobbered(migration_db):
    engine, _ = migration_db
    orphan = Fernet(Fernet.generate_key()).encrypt(b"unknown").decode()
    _insert_media_server(engine, orphan)

    assert reencrypt_legacy_secrets() == 0
    assert _stored_token(engine) == orphan

def test_no_migration_when_the_installation_still_uses_the_legacy_key(migration_db, monkeypatch):
    engine, _ = migration_db
    monkeypatch.setattr(
        "affiche.config.secrets_migration.get_encryption_key",
        lambda: LEGACY_ENCRYPTION_KEY.encode(),
    )
    _insert_media_server(engine, _LEGACY.encrypt(b"plex-token-42").decode())

    assert reencrypt_legacy_secrets() == 0

def test_empty_database_is_a_no_op(migration_db):
    assert reencrypt_legacy_secrets() == 0
