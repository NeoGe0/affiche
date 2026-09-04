import json
import logging

import pytest
from cryptography.fernet import Fernet

from affiche.config.env_config import (
    LEGACY_ENCRYPTION_KEY,
    SECRETS_FILE,
    get_auth_secret,
    get_encryption_key,
    is_using_legacy_encryption_key,
    warn_if_legacy_encryption_key,
)
from affiche.config.secrets_store import get_or_create_secret

@pytest.fixture
def no_secrets_file(monkeypatch, tmp_path):
    path = tmp_path / "secrets.json"
    monkeypatch.setattr("affiche.config.env_config.SECRETS_FILE", str(path))
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    return path

def test_uses_env_key_when_it_is_already_a_fernet_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    assert get_encryption_key() == key.encode()

def test_env_key_is_stripped_of_whitespace_and_quotes(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", f'  "{key}"\n')
    assert get_encryption_key() == key.encode()

def test_arbitrary_env_key_is_derived_into_a_valid_fernet_key(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "a" * 64)
    derived = get_encryption_key()
    Fernet(derived)
    assert derived != b"a" * 64

def test_derivation_is_deterministic(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "correct horse battery staple")
    first = get_encryption_key()
    assert get_encryption_key() == first

def test_derivation_differs_per_passphrase(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "passphrase-one")
    first = get_encryption_key()
    monkeypatch.setenv("ENCRYPTION_KEY", "passphrase-two")
    assert get_encryption_key() != first

def test_generates_and_persists_a_key_when_env_is_unset(no_secrets_file):
    generated = get_encryption_key()
    Fernet(generated)
    assert no_secrets_file.exists()
    assert json.loads(no_secrets_file.read_text())["encryption_key"] == generated.decode()

def test_generated_key_is_stable_across_calls(no_secrets_file):
    assert get_encryption_key() == get_encryption_key()

def test_generated_auth_secret_is_persisted_alongside(no_secrets_file):
    get_encryption_key()
    secret = get_auth_secret()
    stored = json.loads(no_secrets_file.read_text())
    assert stored["auth_secret"] == secret
    assert stored["encryption_key"]

def test_empty_env_value_falls_back_to_generation(monkeypatch, no_secrets_file):
    monkeypatch.setenv("ENCRYPTION_KEY", "")
    assert get_encryption_key() == json.loads(no_secrets_file.read_text())["encryption_key"].encode()

def test_generated_key_is_not_the_legacy_public_key(no_secrets_file):
    assert get_encryption_key() != LEGACY_ENCRYPTION_KEY.encode()
    assert is_using_legacy_encryption_key() is False

def test_legacy_key_is_flagged_and_warned_about(monkeypatch, caplog):
    monkeypatch.setenv("ENCRYPTION_KEY", LEGACY_ENCRYPTION_KEY)
    assert is_using_legacy_encryption_key() is True
    with caplog.at_level(logging.WARNING, logger="affiche.config.env_config"):
        warn_if_legacy_encryption_key()
    assert any("git history" in r.message for r in caplog.records)

def test_no_warning_for_a_private_key(monkeypatch, caplog):
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    with caplog.at_level(logging.WARNING, logger="affiche.config.env_config"):
        warn_if_legacy_encryption_key()
    assert caplog.records == []

def test_env_auth_secret_wins_over_generation(monkeypatch, no_secrets_file):
    monkeypatch.setenv("AUTH_SECRET", "my-own-secret")
    assert get_auth_secret() == "my-own-secret"
    assert not no_secrets_file.exists()

def test_secrets_store_refuses_to_overwrite_a_corrupt_file(tmp_path):
    path = tmp_path / "secrets.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="restore it from a backup"):
        get_or_create_secret(path, "encryption_key", lambda: "generated")
    assert path.read_text(encoding="utf-8") == "{not json"

def test_secrets_file_lives_in_the_config_dir():
    assert SECRETS_FILE.endswith("secrets.json")
