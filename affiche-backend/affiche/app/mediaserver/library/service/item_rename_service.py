import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.model import LibraryItem
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.title_check import matches_any, titles_differ
from affiche.app.mediaserver.service.media_server_connector_protocol import ItemTitleWriter
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository

logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 1024

class ItemRenameError(Exception):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

NO_ID = "no_id"
NOT_CONFIGURED = "not_configured"
NOT_FOUND = "not_found"
ALREADY_CORRECT = "already_correct"

class TitleSuggestions:

    def __init__(self, current: str, matched: Optional[object] = None,
                 reason: Optional[str] = None):
        self.current = current
        self.matched = matched
        self.reason = reason

class ItemRenameService:

    def __init__(self, session: Session, connector_factory: Optional[object] = None,
                 poster_aggregator: Optional[object] = None):
        self._library_repository = LibraryRepository(session)
        self._media_server_repository = MediaServerRepository(session)
        self._connector_factory = connector_factory
        self._poster_aggregator = poster_aggregator

    def suggest_titles(self, media_server_id: int, library_id: int,
                       item_id: int) -> TitleSuggestions:
        item = self._library_repository.get_library_item(library_id, item_id)
        matched = self.catalogue_title(media_server_id, library_id, item_id)

        if matched is None:
            return TitleSuggestions(item.title, reason=self._why_no_answer(item))
        if self.agrees_with_catalogue(media_server_id, library_id, item, matched.title):
            return TitleSuggestions(item.title, reason=ALREADY_CORRECT)
        return TitleSuggestions(item.title, matched=matched)

    def agrees_with_catalogue(self, media_server_id: int, library_id: int, item: LibraryItem,
                              primary: str) -> bool:
        if not titles_differ(item.title, primary):
            return True
        return matches_any(item.title,
                           self.catalogue_alternatives(media_server_id, library_id, item.id))

    def catalogue_alternatives(self, media_server_id: int, library_id: int,
                               item_id: int) -> List[str]:
        self._library_repository.get_library(media_server_id, library_id)
        item = self._library_repository.get_library_item(library_id, item_id)
        if self._poster_aggregator is None or not (item.tmdb_id or item.tvdb_id):
            return []
        return self._poster_aggregator.alternative_titles(
            media_type=item.type, tmdb_id=item.tmdb_id, tvdb_id=item.tvdb_id)

    def catalogue_title(self, media_server_id: int, library_id: int, item_id: int):
        library = self._library_repository.get_library(media_server_id, library_id)
        item = self._library_repository.get_library_item(library_id, item_id)

        if self._poster_aggregator is None or not (item.tmdb_id or item.tvdb_id):
            return None
        language = self._title_language(media_server_id, library)
        if not language:
            return None
        return self._poster_aggregator.title_from_ids(
            media_type=item.type, language=language,
            tmdb_id=item.tmdb_id, tvdb_id=item.tvdb_id,
        )

    def _why_no_answer(self, item: LibraryItem) -> str:
        if self._poster_aggregator is None:
            return NOT_CONFIGURED
        if not (item.tmdb_id or item.tvdb_id):
            return NO_ID
        return NOT_FOUND

    def _title_language(self, media_server_id: int, library) -> Optional[str]:
        language = (getattr(library, 'language', None) or "").strip()
        if language:
            return language[:2].lower()

        try:
            media_server = self._media_server_repository.get(media_server_id)
        except Exception:
            logger.warning("Could not read the language order of media server %s", media_server_id,
                           exc_info=True)
            return None
        return next((code for code in media_server.language_order if code), None)

    def rename_item(self, media_server_id: int, library_id: int, item_id: int,
                    title: str) -> LibraryItem:
        cleaned = title.strip()
        if not cleaned:
            raise ItemRenameError("A title is required.")
        if len(cleaned) > MAX_TITLE_LENGTH:
            raise ItemRenameError(f"A title cannot be longer than {MAX_TITLE_LENGTH} characters.")

        item = self._get_item(media_server_id, library_id, item_id)
        if cleaned == item.title:
            return item

        if not self._writer(media_server_id).rename_item(item.external_id, cleaned):
            raise ItemRenameError("The media server would not rename this item.")

        logger.info("Renamed item %s from '%s' to '%s'", item_id, item.title, cleaned)
        item.title = cleaned
        item.title_mismatched = False
        item.title_checked_at = None
        return self._library_repository.create_or_update_item(item)

    def _get_item(self, media_server_id: int, library_id: int, item_id: int) -> LibraryItem:
        self._library_repository.get_library(media_server_id, library_id)
        return self._library_repository.get_library_item(library_id, item_id)

    def _writer(self, media_server_id: int) -> ItemTitleWriter:
        if self._connector_factory is None:
            raise ItemRenameError("No media server connection is configured.")
        return self._connector_factory.get(media_server_id)
