import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.events import event_manager
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.service.library_session import library_session
from affiche.app.mediaserver.service.media_server_connector_protocol import MediaServerConnector
from affiche.app.mediaserver.service.poster_workers import RESET_MAX_WORKERS
from affiche.app.mediaserver.service.source_poster_service import fetch_as_jpeg

from affiche.app.mediaserver.library.model import LibraryItemSearch, SeasonPosterState

logger = logging.getLogger(__name__)

def was_attempted(item: LibraryItem) -> bool:
    return item.processed or item.error_message is not None

class PosterResetter:

    def __init__(self,
                 file_store: FileStoreService,
                 session_factory: Callable[[], Session]):
        self._file_store = file_store
        self._session_factory = session_factory

    def reset_poster(self,
                     repo: LibraryRepository,
                     item: LibraryItem,
                     connector: MediaServerConnector,
                     include_unprocessed: bool = False):
        if not was_attempted(item) and not include_unprocessed:
            return

        reset = connector.reset_poster(item.external_id)
        if reset.success:
            self._delete_poster(item.library_id, item.id)
            item.processed = False
            item.poster_uploaded_at = None
            item.poster_hash = None
            item.poster_provider = None
            item.style_hash = None
            item.error_message = None
            self._cache_source_poster(item, connector, poster_url=reset.poster_url)
            repo.create_or_update_item(item)
            event_manager.publish_item_processed(item.library_id, item.id, processed=False)

    def reset_season_posters(self,
                             season_service: LibrarySeasonService,
                             item: LibraryItem,
                             connector: MediaServerConnector):
        seasons = season_service.get_item_seasons(item.library_id, item.id)
        reset_seasons = []
        for season in seasons:
            reset = connector.reset_poster(season.external_id)
            if reset.success:
                self._delete_poster(item.library_id, item.id, season_number=season.season_number)
                self._cache_source_poster(item, connector, season=season,
                                          poster_url=reset.poster_url)
                reset_seasons.append(season)
                event_manager.publish_season_processed(
                    item.library_id,
                    item.id,
                    season.season_number,
                    processed=False
                )
        season_service.update_seasons(reset_seasons, SeasonPosterState(
            processed=False,
            poster_hash=None,
            poster_provider=None,
            style_hash=None,
        ))
        if reset_seasons:
            season_service.create_or_update(reset_seasons)

    def reset_library_posters(self,
                              media_server_id: int,
                              library_id: int,
                              connector: MediaServerConnector,
                              cancel_check: Callable[[], bool] = None,
                              include_unprocessed: bool = False):
        with library_session(self._session_factory) as (repo, _):
            items = repo.find_items(LibraryItemSearch(
                library_id=library_id, attempted=None if include_unprocessed else True))
            library_name = repo.get_library(media_server_id, library_id).name

        self.reset_items(items, library_name, connector, cancel_check, include_unprocessed)

    def reset_items(self,
                    items: List[LibraryItem],
                    library_name: str,
                    connector: MediaServerConnector,
                    cancel_check: Callable[[], bool] = None,
                    include_unprocessed: bool = False):
        logger.info("Resetting %d items in '%s' using %d workers",
                    len(items), library_name, RESET_MAX_WORKERS)

        def reset_item(item: LibraryItem):
            with library_session(self._session_factory) as (repository, session):
                try:
                    self.reset_poster(repository, item, connector, include_unprocessed)
                    if item.type == 'show':
                        season_service = LibrarySeasonService(session)
                        self.reset_season_posters(season_service, item, connector)
                except Exception:
                    logger.exception("Failed to reset poster for item %s", item.id)

        total = len(items)
        progress_label = f"Resetting posters — {library_name}"
        report_task_progress(0, total, progress_label)
        done = 0

        with ThreadPoolExecutor(max_workers=RESET_MAX_WORKERS) as executor:
            futures = {executor.submit(reset_item, item): item for item in items}
            for future in as_completed(futures):
                if cancel_check and cancel_check():
                    logger.info("Reset cancelled, shutting down executor")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return
                item = futures[future]
                try:
                    future.result()
                except Exception:
                    logger.exception("[reset] item %s (%s): FAILED (exception)", item.id, item.title)
                done += 1
                report_task_progress(done, total, progress_label)

    def _cache_source_poster(self,
                             item: LibraryItem,
                             connector: MediaServerConnector,
                             season: Optional[LibrarySeason] = None,
                             poster_url: Optional[str] = None):
        target = season or item
        season_number = season.season_number if season else None
        try:
            poster_url = poster_url or connector.get_poster_url(target.external_id)
            if not poster_url:
                logger.warning("No poster URL after reset for item %s (%s)", item.id, item.title)
                return
            jpeg = fetch_as_jpeg(poster_url)
            self._file_store.save(item.library_id, item.id, jpeg, season_number=season_number)
            target.poster_url = poster_url
        except Exception:
            logger.warning("Could not cache the reset poster for item %s (%s)", item.id, item.title,
                           exc_info=True)

    def _delete_poster(self,
                       library_id: int,
                       item_id: int,
                       season_number: Optional[int] = None):
        self._file_store.delete(library_id,
                                item_id,
                                season_number=season_number)
