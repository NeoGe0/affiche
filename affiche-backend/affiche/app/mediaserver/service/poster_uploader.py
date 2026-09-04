import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from affiche.app.filestore.filestore import FileStoreService
from affiche.app.mediaserver.library.collections.model.library_collection import LibraryCollection
from affiche.app.mediaserver.library.model import Library
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.service.library_session import library_session
from affiche.app.mediaserver.service.media_server_connector_protocol import MediaServerConnector
from affiche.app.mediaserver.service.poster_workers import MAX_WORKERS

from affiche.app.mediaserver.library.model import LibraryItemSearch, SeasonPosterState

logger = logging.getLogger(__name__)

class PosterUploader:

    def __init__(self,
                 file_store: FileStoreService,
                 session_factory: Callable[[], Session]):
        self._file_store = file_store
        self._session_factory = session_factory

    def upload_poster(self,
                      external_id: str,
                      poster_path: str,
                      connector: MediaServerConnector) -> bool:
        try:
            return bool(connector.upload_poster(external_id, poster_path))
        except Exception:
            logger.exception("Failed to upload poster for external_id %s", external_id)
            return False

    def upload_if_changed(self,
                          item: LibraryItem,
                          poster_path: str,
                          digest: Optional[str],
                          connector: MediaServerConnector) -> bool:
        if digest and item.poster_hash == digest:
            logger.info("[upload] item %s (%s): unchanged, skipped", item.id, item.title)
            item.poster_uploaded_at = item.poster_uploaded_at or datetime.now(timezone.utc)
            return True

        if not self.upload_poster(item.external_id, poster_path, connector):
            return False

        item.poster_hash = digest
        item.poster_uploaded_at = datetime.now(timezone.utc)
        return True

    def upload_existing_item_poster(self,
                                    item: LibraryItem,
                                    connector: MediaServerConnector) -> bool:
        if not self._file_store.exists(item.library_id, item.id):
            logger.warning("[upload] item %s (%s): no stored poster to upload", item.id, item.title)
            return False

        poster_path = str(self._file_store.path(item.library_id, item.id))
        digest = self._file_store.digest(item.library_id, item.id)
        if not self.upload_if_changed(item, poster_path, digest, connector):
            logger.warning("[upload] item %s (%s): FAILED", item.id, item.title)
            return False

        with library_session(self._session_factory) as (repo, _):
            repo.create_or_update_item(item)
        logger.info("[upload] item %s (%s): SUCCESS", item.id, item.title)
        return True

    def upload_collection_if_changed(self,
                                     collection: LibraryCollection,
                                     poster_path: str,
                                     digest: Optional[str],
                                     connector: MediaServerConnector) -> bool:
        if digest and collection.poster_hash == digest:
            logger.info("[upload] collection %s (%s): unchanged, skipped",
                        collection.id, collection.title)
            collection.poster_uploaded_at = (collection.poster_uploaded_at
                                             or datetime.now(timezone.utc))
            return True

        if not self.upload_poster(collection.external_id, poster_path, connector):
            return False

        collection.poster_hash = digest
        collection.poster_uploaded_at = datetime.now(timezone.utc)
        return True

    def upload_season_if_changed(self,
                                 season_service: LibrarySeasonService,
                                 season: LibrarySeason,
                                 item: LibraryItem,
                                 poster_path: str,
                                 digest: Optional[str],
                                 connector: MediaServerConnector) -> bool:
        if digest and season.poster_hash == digest:
            logger.info("[upload] season %d of '%s': unchanged, skipped", season.season_number, item.title)
            return True

        if not self.upload_poster(season.external_id, poster_path, connector):
            return False

        season.poster_hash = digest
        season_service.update_seasons([season], SeasonPosterState(poster_hash=digest))
        return True

    def upload_existing_season_posters(self,
                                       season_service: LibrarySeasonService,
                                       item: LibraryItem,
                                       connector: MediaServerConnector):
        seasons = season_service.get_item_seasons(item.library_id, item.id)
        for season in seasons:
            if not self._file_store.exists(item.library_id, item.id, season_number=season.season_number):
                continue
            poster_path = str(self._file_store.path(item.library_id, item.id,
                                                    season_number=season.season_number))
            digest = self._file_store.digest(item.library_id, item.id,
                                             season_number=season.season_number)
            self.upload_season_if_changed(season_service, season, item, poster_path, digest, connector)

    def upload_library_posters(self,
                               library: Library,
                               connector: MediaServerConnector,
                               cancel_check: Callable[[], bool] = None):
        with library_session(self._session_factory) as (repo, _):
            items = repo.find_items(LibraryItemSearch(
                library_id=library.id, processed=True, uploaded=False))

        self.upload_items(items, library.name, connector, cancel_check)

    def upload_items(self,
                     items: List[LibraryItem],
                     library_name: str,
                     connector: MediaServerConnector,
                     cancel_check: Callable[[], bool] = None):
        logger.info("Uploading %d posters in '%s' using %d workers",
                    len(items), library_name, MAX_WORKERS)

        uploaded = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.upload_existing_item_poster, item, connector): item
                       for item in items}
            for future in as_completed(futures):
                if cancel_check and cancel_check():
                    logger.info("Upload cancelled, shutting down executor")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return
                item = futures[future]
                try:
                    if future.result():
                        uploaded += 1
                    else:
                        failed += 1
                except Exception:
                    logger.exception("[upload] item %s (%s): FAILED (exception)", item.id, item.title)
                    failed += 1

        logger.info("'%s' upload complete: %d uploaded, %d failed", library_name, uploaded, failed)
