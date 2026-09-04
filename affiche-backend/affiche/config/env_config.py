import base64
import logging
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from dotenv import load_dotenv

from affiche.config.secrets_store import get_or_create_secret

load_dotenv()

logger = logging.getLogger(__name__)

_DEV_CONFIG_DIR = Path(__file__).resolve().parents[2] / "data" / "config"
CONFIG_DIR = os.getenv("CONFIG_DIR") or str(_DEV_CONFIG_DIR)
_CONFIG_PATH = Path(CONFIG_DIR)

GLOBAL_CONFIGURATION_DIR = CONFIG_DIR

DB_DIR = str(_CONFIG_PATH / "db")

FILESTORE_DIR = str(_CONFIG_PATH / "posters")

LOG_DIR = str(_CONFIG_PATH / "log")

USER_FONTS_DIR = str(_CONFIG_PATH / "fonts")

POSTER_CONFIG_FILE = str(_CONFIG_PATH / "poster_config.json")

CUSTOM_POSTER_DIR = str(_CONFIG_PATH / "custom-posters")

APP_SETTINGS_FILE = str(_CONFIG_PATH / "app_settings.json")

SECRETS_FILE = str(_CONFIG_PATH / "secrets.json")

LEGACY_ENCRYPTION_KEY = "3oPpJ6KzQ5b8k5f3hPZg0FQ1VZk9QXyqZzQ0Yy7vQdM="

def _clean_secret(raw: str | None) -> str:
    value = (raw or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value

def _derive_fernet_key(passphrase: str) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"imagarr:encryption-key")
    return base64.urlsafe_b64encode(hkdf.derive(passphrase.encode()))

def _coerce_fernet_key(raw: str) -> bytes:
    candidate = raw.encode()
    try:
        Fernet(candidate)
    except (ValueError, TypeError):
        return _derive_fernet_key(raw)
    return candidate

def get_encryption_key() -> bytes:
    configured = _clean_secret(os.getenv("ENCRYPTION_KEY"))
    if configured:
        return _coerce_fernet_key(configured)
    generated = get_or_create_secret(
        Path(SECRETS_FILE), "encryption_key", lambda: Fernet.generate_key().decode()
    )
    return generated.encode()

def get_auth_secret() -> str:
    configured = _clean_secret(os.getenv("AUTH_SECRET"))
    if configured:
        return configured
    return get_or_create_secret(
        Path(SECRETS_FILE), "auth_secret", lambda: secrets.token_urlsafe(48)
    )

def is_using_legacy_encryption_key() -> bool:
    return get_encryption_key() == LEGACY_ENCRYPTION_KEY.encode()

def warn_if_legacy_encryption_key() -> None:
    if is_using_legacy_encryption_key():
        logger.warning(
            "ENCRYPTION_KEY is set to the public key that used to ship as this app's "
            "default — it is in the git history, so stored service tokens are readable "
            "by anyone. Unset it to have a private key generated instead."
        )
