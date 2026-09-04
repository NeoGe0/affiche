from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.settings.connector.library_settings_entity import (
    LibrarySettingsEntity,
)
from affiche.app.style_profile.connector.style_profile_entity import StyleProfileEntity
from affiche.app.style_profile.model.style_profile import StyleProfile

class AlchemyStyleProfileConnector:

    def __init__(self, session: Session):
        self._session = session

    def get(self, profile_id: int) -> Optional[StyleProfile]:
        entity = self._session.get(StyleProfileEntity, profile_id)
        return StyleProfile.model_validate(entity) if entity else None

    def find_by_name(self, name: str) -> Optional[StyleProfile]:
        entity = (self._session.query(StyleProfileEntity)
                  .filter(func.lower(StyleProfileEntity.name) == name.strip().lower())
                  .first())
        return StyleProfile.model_validate(entity) if entity else None

    def list_all(self) -> List[StyleProfile]:
        entities = (self._session.query(StyleProfileEntity)
                    .order_by(func.lower(StyleProfileEntity.name))
                    .all())
        return [StyleProfile.model_validate(entity) for entity in entities]

    def create(self, profile: StyleProfile) -> StyleProfile:
        entity = StyleProfileEntity(**profile.model_dump(exclude={"id", "created_at", "updated_at"}))
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return StyleProfile.model_validate(entity)

    def update(self, profile: StyleProfile) -> StyleProfile:
        entity = self._session.get(StyleProfileEntity, profile.id)
        if not entity:
            raise ValueError(f"Style profile {profile.id} not found")

        for field, value in profile.model_dump(
                exclude={"id", "created_at", "updated_at"}).items():
            setattr(entity, field, value)

        self._session.commit()
        self._session.refresh(entity)
        return StyleProfile.model_validate(entity)

    def delete(self, profile_id: int) -> bool:
        entity = self._session.get(StyleProfileEntity, profile_id)
        if not entity:
            return False

        (self._session.query(LibrarySettingsEntity)
         .filter(LibrarySettingsEntity.style_profile_id == profile_id)
         .update({LibrarySettingsEntity.style_profile_id: None}, synchronize_session=False))

        self._session.delete(entity)
        self._session.commit()
        return True

    def count_libraries_using(self, profile_id: int) -> int:
        return (self._session.query(func.count())
                .select_from(LibrarySettingsEntity)
                .filter(LibrarySettingsEntity.style_profile_id == profile_id)
                .scalar()) or 0
