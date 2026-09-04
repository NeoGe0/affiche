import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

def get_or_create_secret(path: Path, name: str, factory: Callable[[], str]) -> str:
    stored = _read(path)
    existing = stored.get(name)
    if isinstance(existing, str) and existing:
        return existing

    value = factory()
    stored[name] = value
    _write(path, stored)
    logger.info("Generated a new %r and stored it in %s", name, path)
    return value

def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(
            f"{path} is not readable JSON ({exc}). It holds this installation's "
            "encryption key: restore it from a backup rather than deleting it — "
            "deleting it makes every stored service token undecryptable."
        ) from exc
    if not isinstance(content, dict):
        raise RuntimeError(f"{path} should contain a JSON object, got {type(content).__name__}.")
    return content

def _write(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".secrets-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
