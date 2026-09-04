from typing import Any, List, Optional

from sqlalchemy.orm import Session

from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.style_profile.model.style_profile import StyleProfile
from affiche.app.style_profile.service.style_profile_repository import StyleProfileRepository
from affiche.config.exceptions.exceptions import StyleProfileNotFoundException

class DuplicateProfileNameError(ValueError):

    def __init__(self, name: str):
        super().__init__(name)
        self.message = f'A style profile named "{name}" already exists'

class StyleProfileService:

    def __init__(self, session: Session):
        self._repository = StyleProfileRepository(session)

    def list_profiles(self) -> List[StyleProfile]:
        return self._repository.list_all()

    def get_profile(self, profile_id: int) -> StyleProfile:
        profile = self._repository.get(profile_id)
        if not profile:
            raise StyleProfileNotFoundException(profile_id)
        return profile

    def create_profile(self,
                       name: str,
                       overlay_options: Optional[dict[str, Any]] = None,
                       text_options: Optional[dict[str, Any]] = None) -> StyleProfile:
        name = name.strip()
        self._assert_name_free(name)
        return self._repository.create(StyleProfile(
            name=name,
            overlay_options=_validated(OverlayOptions, overlay_options),
            text_options=_validated(TextOptions, text_options),
        ))

    def update_profile(self,
                       profile_id: int,
                       updates: dict[str, Any]) -> StyleProfile:
        profile = self.get_profile(profile_id)

        if "name" in updates:
            name = (updates["name"] or "").strip()
            self._assert_name_free(name, exclude_id=profile_id)
            profile.name = name
        if "overlay_options" in updates:
            profile.overlay_options = _validated(OverlayOptions, updates["overlay_options"])
        if "text_options" in updates:
            profile.text_options = _validated(TextOptions, updates["text_options"])

        return self._repository.update(profile)

    def delete_profile(self, profile_id: int) -> None:
        if not self._repository.delete(profile_id):
            raise StyleProfileNotFoundException(profile_id)

    def count_libraries_using(self, profile_id: int) -> int:
        return self._repository.count_libraries_using(profile_id)

    def _assert_name_free(self, name: str, exclude_id: Optional[int] = None) -> None:
        existing = self._repository.find_by_name(name)
        if existing and existing.id != exclude_id:
            raise DuplicateProfileNameError(name)

def _validated(model, stored: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if stored is None:
        return None
    return model(**stored).model_dump()
