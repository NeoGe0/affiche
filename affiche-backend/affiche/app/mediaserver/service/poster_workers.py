import logging
import os

logger = logging.getLogger(__name__)

MAX_WORKERS = 4

def _env_worker_count(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Ignoring %s=%r: not an integer, using %d", name, raw, default)
        return default
    if value < 1:
        logger.warning("Ignoring %s=%d: must be at least 1, using %d", name, value, default)
        return default
    return value

RESET_MAX_WORKERS = _env_worker_count("RESET_MAX_WORKERS", MAX_WORKERS)
