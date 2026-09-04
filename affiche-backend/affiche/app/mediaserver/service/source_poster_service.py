import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from io import BytesIO
from typing import Callable, ContextManager, List, Optional, Tuple

from PIL import Image
from sqlalchemy.orm import Session

from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.events import event_manager
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.image.image_composer import ImageComposer
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.service.poster_workers import MAX_WORKERS

from affiche.app.mediaserver.library.model import LibraryItemSearch

logger = logging.getLogger(__name__)

def fetch_as_jpeg(url: str) -> bytes:
    raw = ImageComposer._download_image(url)
    image = Image.open(BytesIO(raw)).convert("RGB")
    output = BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()

class SourcePosterService:

    def __init__(self,
                 session_factory: Callable[[], Session],
                 file_store: FileStoreService):
        self._session_factory = session_factory
        self._file_store = file_store

    def download_source_posters(self,
                                media_server_id: int,
                                library_id: int = None,
                                cancel_check: Callable[[], bool] = None):
        with self._session_scope() as (repo, _):
            if library_id:
                libraries = [repo.get_library(media_server_id, library_id)]
            else:
                libraries = repo.find_libraries(LibrarySearch(media_server_id=media_server_id, enabled=True))

        for library in libraries:
            if cancel_check and cancel_check():
                logger.info("Source poster download cancelled")
                return
            self._download_library_source_posters(library, cancel_check)

    def _download_library_source_posters(self,
                                         library: Library,
                                         cancel_check: Callable[[], bool] = None):
        library_id = library.id

        with self._session_scope() as (repo, session):
            items = repo.find_items(LibraryItemSearch(library_id=library_id))
            season_service = LibrarySeasonService(session)
            seasons_by_item = {
                item.id: season_service.get_item_seasons(library_id, item.id)
                for item in items if item.type == 'show'
            }

        jobs: List[Tuple[str, LibraryItem, Optional[LibrarySeason]]] = []
        for item in items:
            if (item.poster_url and not item.processed
                    and not self._file_store.exists(library_id, item.id)):
                jobs.append(('item', item, None))
            for season in seasons_by_item.get(item.id, []):
                if (season.poster_url and not season.processed
                        and not self._file_store.exists(library_id, item.id,
                                                        season_number=season.season_number)):
                    jobs.append(('season', item, season))

        if not jobs:
            logger.info("No source posters to download for library '%s'", library.name)
            return

        logger.info("Downloading %d source posters for library '%s'", len(jobs), library.name)
        total = len(jobs)
        progress_label = f"Syncing posters — {library.name}"
        report_task_progress(0, total, progress_label)
        downloaded = 0
        done = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self._download_source_poster, *job): job for job in jobs}
            for future in as_completed(futures):
                if cancel_check and cancel_check():
                    logger.info("Source poster download cancelled for library '%s'", library.name)
                    executor.shutdown(wait=False, cancel_futures=True)
                    return
                kind, item, season = futures[future]
                try:
                    if future.result():
                        downloaded += 1
                except Exception:
                    logger.exception("[source-download] item %s (%s) %s: FAILED (exception)",
                                     item.id, item.title, kind)
                done += 1
                report_task_progress(done, total, progress_label)
        logger.info("Library '%s' source posters: %d downloaded", library.name, downloaded)

    def _download_source_poster(self,
                                kind: str,
                                item: LibraryItem,
                                season: Optional[LibrarySeason]) -> bool:
        try:
            if kind == 'season':
                jpeg = fetch_as_jpeg(season.poster_url)
                self._file_store.save(item.library_id, item.id, jpeg,
                                      season_number=season.season_number)
                event_manager.publish_season_processed(
                    item.library_id, item.id, season.season_number, processed=season.processed
                )
            else:
                jpeg = fetch_as_jpeg(item.poster_url)
                self._file_store.save(item.library_id, item.id, jpeg)
                event_manager.publish_item_processed(
                    item.library_id, item.id, processed=item.processed
                )
            label = "season %d" % season.season_number if kind == 'season' else "poster"
            logger.info("[source-download] item %s (%s) %s: SUCCESS", item.id, item.title, label)
            return True
        except Exception:
            label = "season %d" % season.season_number if kind == 'season' else "poster"
            logger.warning("[source-download] item %s (%s) %s: FAILED", item.id, item.title, label,
                           exc_info=True)
            return False

    @contextmanager
    def _session_scope(self) -> ContextManager[Tuple[LibraryRepository, Session]]:
        session = self._session_factory()
        repo = LibraryRepository(session)
        try:
            yield repo, session
        finally:
            session.close()
