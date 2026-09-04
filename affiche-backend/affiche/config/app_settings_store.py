import json
import logging
import os
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List

from affiche.config.env_config import APP_SETTINGS_FILE
from affiche.config.library_config import DEFAULT_PROVIDER_ORDER
from affiche.config.logging_config import set_log_level

logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

@dataclass
class AppSettings:
    new_library_enabled: bool = True
    new_library_upload_enabled: bool = True
    new_library_provider_order: List[str] = field(default_factory=lambda: list(DEFAULT_PROVIDER_ORDER))
    log_level: str = "INFO"
    trash_retention_days: int = 30

    def __post_init__(self):
        self.log_level = (self.log_level or "INFO").upper()
        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError(f"log_level must be one of {VALID_LOG_LEVELS}, got {self.log_level}")
        if self.trash_retention_days < 0:
            raise ValueError(f"trash_retention_days must be >= 0, got {self.trash_retention_days}")

    def model_dump(self) -> dict:
        return asdict(self)

class AppSettingsStore:
    def __init__(self, path: str = APP_SETTINGS_FILE):
        self._path = Path(path)

    def get(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()
        try:
            return AppSettings(**json.loads(self._path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            logger.warning("Invalid app settings at %s; using defaults", self._path, exc_info=True)
            return AppSettings()

    def partial_update(self, changes: dict) -> AppSettings:
        merged = self.get().model_dump()
        merged.update(changes)

        settings = AppSettings(**merged)
        self.save(settings)
        if "log_level" in changes:
            set_log_level(settings.log_level)
        return settings

    def save(self, settings: AppSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(settings.model_dump(), indent=2)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self._path)
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
