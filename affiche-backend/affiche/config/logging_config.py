import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from affiche.config.env_config import LOG_DIR
from affiche.config.redaction import RedactingFormatter

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
ACCESS_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

_ROTATE_WHEN = "midnight"
_BACKUP_COUNT = 14

def _timed_file_handler(path: Path, formatter: logging.Formatter, level: int) -> TimedRotatingFileHandler:
    handler = TimedRotatingFileHandler(
        str(path), when=_ROTATE_WHEN, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler

def _initial_level() -> int:
    try:
        from affiche.config.app_settings_store import AppSettingsStore
        return getattr(logging, AppSettingsStore().get().log_level, logging.INFO)
    except Exception:
        return logging.INFO

def set_log_level(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)

def setup_logging():
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = _initial_level()
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)

    redacting_formatter = RedactingFormatter(LOG_FORMAT)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(redacting_formatter)
    root_logger.addHandler(
        _timed_file_handler(log_dir / "affiche.log", redacting_formatter, level)
    )

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.addHandler(
        _timed_file_handler(
            log_dir / "access.log", RedactingFormatter(ACCESS_LOG_FORMAT), logging.INFO
        )
    )
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False

    logging.getLogger("apscheduler.executors").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
