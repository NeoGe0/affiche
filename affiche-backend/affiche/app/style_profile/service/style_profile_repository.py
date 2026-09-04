from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.style_profile.connector.alchemy_style_profile_connector import (
    AlchemyStyleProfileConnector,
)
from affiche.app.style_profile.model.style_profile import StyleProfile

class StyleProfileRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyStyleProfileConnector(session)

    def get(self, profile_id: int) -> Optional[StyleProfile]:
        return self._connector.get(profile_id)

    def find_by_name(self, name: str) -> Optional[StyleProfile]:
        return self._connector.find_by_name(name)

    def list_all(self) -> List[StyleProfile]:
        return self._connector.list_all()

    def create(self, profile: StyleProfile) -> StyleProfile:
        return self._connector.create(profile)

    def update(self, profile: StyleProfile) -> StyleProfile:
        return self._connector.update(profile)

    def delete(self, profile_id: int) -> bool:
        return self._connector.delete(profile_id)

    def count_libraries_using(self, profile_id: int) -> int:
        return self._connector.count_libraries_using(profile_id)
