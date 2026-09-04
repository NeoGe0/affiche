from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.settings.library_settings_repository import LibrarySettingsRepository
from affiche.app.mediaserver.library.settings.model.library_settings import LibrarySettings
from affiche.config.app_settings_store import AppSettingsStore

NULLABLE_FIELDS = frozenset({"overlay_options", "text_options", "style_profile_id"})

class LibrarySettingsService:

    def __init__(self, session: Session):
        self._repository = LibrarySettingsRepository(session)
        self._library_repository = LibraryRepository(session)

    def get_settings(self,
                     library_id: int) -> Optional[LibrarySettings]:
        return self._repository.get(library_id)

    def get_settings_or_default(self,
                                library_id: int) -> LibrarySettings:
        return self.get_settings(library_id) or self._default_settings(library_id)

    def _default_settings(self,
                          library_id: int) -> LibrarySettings:
        app_defaults = AppSettingsStore().get()
        return LibrarySettings(
            library_id=library_id,
            upload_enabled=app_defaults.new_library_upload_enabled,
            provider_order=list(app_defaults.new_library_provider_order),
        )

    def create_settings(self,
                        library_id: int) -> LibrarySettings:
        return self._repository.create(self._default_settings(library_id))

    def partial_update_settings(self,
                                library_id: int,
                                updates: dict[str, Any]) -> LibrarySettings:
        settings = self.get_settings(library_id) or self._default_settings(library_id)
        for field, value in updates.items():
            if value is not None or field in NULLABLE_FIELDS:
                setattr(settings, field, value)
        return self._repository.upsert(settings)

    def is_enabled(self, media_server_id: int, library_id: int) -> bool:
        return self._library_repository.get_library(media_server_id, library_id).enabled

    def set_enabled(self, media_server_id: int, library_id: int, enabled: bool) -> bool:
        return self._library_repository.set_library_enabled(
            media_server_id, library_id, enabled).enabled

    def mark_full_sync(self, library_id: int, at: datetime) -> None:
        if self._repository.get(library_id) is None:
            self._repository.create(self._default_settings(library_id))
        self._repository.set_last_full_sync(library_id, at)

    def delete_settings(self, library_id: int) -> bool:
        return self._repository.delete(library_id)
