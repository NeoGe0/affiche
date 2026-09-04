import logging
from typing import List, NamedTuple, Optional

from affiche.app.filestore.filestore import FileStoreService
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.external.poster.poster_service import PosterAggregatorService

logger = logging.getLogger(__name__)

class ServerPosterSettings(NamedTuple):
    language_order: List[str]
    fallback_to_server_poster: bool
    skip_style_when_not_textless: bool

SERVER_PROVIDER = "server"

class PosterSource(NamedTuple):
    source: str
    styled: bool
    provider: str

class PosterResolver:

    def __init__(self,
                 poster_aggregator: PosterAggregatorService,
                 file_store: FileStoreService):
        self._poster_aggregator = poster_aggregator
        self._file_store = file_store

    def resolve_item_poster(self,
                            item: LibraryItem,
                            media_type: str,
                            provider_order: List[str],
                            settings: ServerPosterSettings) -> Optional[PosterSource]:
        for language in settings.language_order:
            found = self._poster_aggregator.find_best_poster(
                title=item.title,
                tmdb_id=item.tmdb_id,
                tvdb_id=item.tvdb_id,
                media_type=media_type,
                provider_order=provider_order,
                language=language or None,
            )
            if found:
                return PosterSource(found.url, self._should_style(language, settings), found.provider)

        if settings.fallback_to_server_poster:
            source = self._server_poster_source(item)
            if source:
                logger.info("[generation] item %s (%s): no provider poster, falling back to the "
                            "media server's own artwork", item.id, item.title)
                return PosterSource(source, True, SERVER_PROVIDER)
        return None

    def resolve_season_poster(self,
                              item: LibraryItem,
                              season: LibrarySeason,
                              provider_order: List[str],
                              settings: ServerPosterSettings) -> Optional[PosterSource]:
        for language in settings.language_order:
            found = self._poster_aggregator.find_best_season_poster(
                title=item.title,
                tmdb_id=item.tmdb_id,
                tvdb_id=item.tvdb_id,
                season_number=season.season_number,
                provider_order=provider_order,
                language=language or None,
            )
            if found:
                return PosterSource(found.url, self._should_style(language, settings), found.provider)

        if settings.fallback_to_server_poster:
            source = self._server_poster_source(item, season=season)
            if source:
                logger.info("[generation] season %d of '%s': no provider poster, falling back to "
                            "the media server's own artwork", season.season_number, item.title)
                return PosterSource(source, True, SERVER_PROVIDER)
        return None

    @staticmethod
    def _should_style(language: str, settings: ServerPosterSettings) -> bool:
        return not (language and settings.skip_style_when_not_textless)

    def _server_poster_source(self,
                              item: LibraryItem,
                              season: Optional[LibrarySeason] = None) -> Optional[str]:
        target = season or item
        if target.poster_hash is not None:
            return None

        season_number = season.season_number if season else None
        if not target.processed and self._file_store.exists(item.library_id, item.id,
                                                            season_number=season_number):
            return str(self._file_store.path(item.library_id, item.id,
                                             season_number=season_number))
        return target.poster_url or None
