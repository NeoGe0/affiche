from typing import Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.settings.connector.alchemy_library_settings_connector import (
    AlchemyLibrarySettingsConnector,
)
from affiche.app.mediaserver.library.settings.model.library_settings import LibrarySettings

class LibrarySettingsRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyLibrarySettingsConnector(session)

    def get(self, library_id: int) -> Optional[LibrarySettings]:
        return self._connector.get(library_id)

    def create(self, settings: LibrarySettings) -> LibrarySettings:
        return self._connector.create(settings)

    def update(self, settings: LibrarySettings) -> LibrarySettings:
        return self._connector.update(settings)

    def upsert(self, settings: LibrarySettings) -> LibrarySettings:
        return self._connector.upsert(settings)

    def set_last_full_sync(self, library_id: int, at) -> bool:
        return self._connector.set_last_full_sync(library_id, at)

    def delete(self, library_id: int) -> bool:
        return self._connector.delete(library_id)
