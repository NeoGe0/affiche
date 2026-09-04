import logging
from typing import NamedTuple, Optional

from sqlalchemy.orm import Session

from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.style_profile.service.style_profile_repository import StyleProfileRepository

logger = logging.getLogger(__name__)

class LibraryPosterStyle(NamedTuple):
    overlay_options: Optional[OverlayOptions] = None
    text_options: Optional[TextOptions] = None

GLOBAL_STYLE = LibraryPosterStyle()

def resolve_library_style(session: Session, library_id: int) -> LibraryPosterStyle:
    settings = LibrarySettingsService(session).get_settings(library_id)
    if not settings:
        return GLOBAL_STYLE

    source = settings
    if settings.style_profile_id is not None:
        profile = StyleProfileRepository(session).get(settings.style_profile_id)
        if profile:
            source = profile
        else:
            logger.warning("Library %d references missing style profile %d, falling back",
                           library_id, settings.style_profile_id)

    return LibraryPosterStyle(
        overlay_options=_parse_style(OverlayOptions, source.overlay_options, library_id),
        text_options=_parse_style(TextOptions, source.text_options, library_id),
    )

def _parse_style(model, stored: Optional[dict], library_id: int):
    if not stored:
        return None
    try:
        return model(**stored)
    except Exception:
        logger.warning("Library %d has unreadable %s, falling back to the global style",
                       library_id, model.__name__, exc_info=True)
        return None
