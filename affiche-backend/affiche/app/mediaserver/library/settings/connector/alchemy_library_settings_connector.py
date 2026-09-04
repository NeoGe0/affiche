from typing import Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.settings.connector.library_settings_entity import (
    LibrarySettingsEntity,
)
from affiche.app.mediaserver.library.settings.model.library_settings import LibrarySettings

class AlchemyLibrarySettingsConnector:

    def __init__(self, session: Session):
        self._session = session

    def get(self, library_id: int) -> Optional[LibrarySettings]:
        entity = self._session.get(LibrarySettingsEntity, library_id)
        return LibrarySettings.model_validate(entity) if entity else None

    def create(self, settings: LibrarySettings) -> LibrarySettings:
        entity = LibrarySettingsEntity(**settings.model_dump())
        self._session.add(entity)
        self._session.flush()
        return LibrarySettings.model_validate(entity)

    def update(self, settings: LibrarySettings) -> LibrarySettings:
        entity = self._session.get(LibrarySettingsEntity, settings.library_id)
        if not entity:
            raise ValueError(f"Settings not found for library {settings.library_id}")

        for field, value in settings.model_dump(exclude={"library_id"}).items():
            setattr(entity, field, value)

        self._session.commit()
        self._session.refresh(entity)
        return LibrarySettings.model_validate(entity)

    def upsert(self, settings: LibrarySettings) -> LibrarySettings:
        entity = self._session.get(LibrarySettingsEntity, settings.library_id)
        if entity:
            for field, value in settings.model_dump(exclude={"library_id"}).items():
                setattr(entity, field, value)
        else:
            entity = LibrarySettingsEntity(**settings.model_dump())
            self._session.add(entity)

        self._session.commit()
        self._session.refresh(entity)
        return LibrarySettings.model_validate(entity)

    def set_last_full_sync(self, library_id: int, at) -> bool:
        entity = self._session.get(LibrarySettingsEntity, library_id)
        if not entity:
            return False

        entity.last_full_sync_at = at
        self._session.commit()
        return True

    def delete(self, library_id: int) -> bool:
        entity = self._session.get(LibrarySettingsEntity, library_id)
        if not entity:
            return False

        self._session.delete(entity)
        self._session.commit()
        return True
