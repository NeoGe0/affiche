import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import inspect, text

from affiche.config.database import SessionLocal
from affiche.config.env_config import LEGACY_ENCRYPTION_KEY, get_encryption_key

logger = logging.getLogger(__name__)

_ENCRYPTED_COLUMNS = (
    ("media_server", "token"),
    ("service_configuration", "token"),
)

def reencrypt_legacy_secrets() -> int:
    current_key = get_encryption_key()
    if current_key == LEGACY_ENCRYPTION_KEY.encode():
        return 0

    legacy = Fernet(LEGACY_ENCRYPTION_KEY.encode())
    current = Fernet(current_key)
    migrated = 0

    with SessionLocal() as session:
        existing = set(inspect(session.get_bind()).get_table_names())
        for table, column in _ENCRYPTED_COLUMNS:
            if table not in existing:
                continue
            rows = session.execute(text(f"SELECT id, {column} FROM {table}")).all()
            for row_id, ciphertext in rows:
                if not ciphertext:
                    continue
                plaintext = _decrypt_if_legacy(ciphertext, legacy, current)
                if plaintext is None:
                    continue
                session.execute(
                    text(f"UPDATE {table} SET {column} = :value WHERE id = :id"),
                    {"value": current.encrypt(plaintext).decode(), "id": row_id},
                )
                migrated += 1
        if migrated:
            session.commit()

    if migrated:
        logger.warning(
            "Re-encrypted %d stored token(s) that were using the old public default key. "
            "They are now protected by this installation's private key.",
            migrated,
        )
    return migrated

def _decrypt_if_legacy(ciphertext: str, legacy: Fernet, current: Fernet) -> bytes | None:
    raw = ciphertext.encode()
    try:
        current.decrypt(raw)
        return None
    except InvalidToken:
        pass
    try:
        return legacy.decrypt(raw)
    except InvalidToken:
        logger.warning(
            "A stored token decrypts with neither the current nor the legacy key; "
            "leaving it untouched. Re-enter that service's token in the UI."
        )
        return None
