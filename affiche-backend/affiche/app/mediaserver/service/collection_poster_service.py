import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional, Union

from sqlalchemy.orm import Session

from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.events import event_manager
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.image.poster_decorator_service import PosterDecorationService
from affiche.app.mediaserver.library.collections.library_collection_repository import (
    LibraryCollectionRepository,
)
from affiche.app.mediaserver.library.model import LibraryItemSearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.collections.model.library_collection import (
    CollectionPosterState,
    LibraryCollection,
    LibraryCollectionSearch,
)
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.mediaserver.service.library_style import resolve_library_style
from affiche.app.mediaserver.service.poster_uploader import PosterUploader
from affiche.app.mediaserver.service.poster_workers import MAX_WORKERS
from affiche.app.mediaserver.service.source_poster_service import fetch_as_jpeg
from affiche.app.provider_stats import ProviderStatsService

logger = logging.getLogger(__name__)

COLLECTION_PROVIDER = "server"

MANUAL_PROVIDER = "manual"

TMDB_PROVIDER = "tmdb"

class CollectionPosterService:

    def __init__(self,
                 session_factory: Callable[[], Session],
                 file_store: FileStoreService,
                 decorator: PosterDecorationService,
                 aggregator_factory: Optional[Callable[[Session], object]] = None,
                 connector_factory: Optional[object] = None):
        self._session_factory = session_factory
        self._file_store = file_store
        self._decorator = decorator
        self._aggregator_factory = aggregator_factory
        self._connector_factory = connector_factory
        self._uploader = PosterUploader(file_store, session_factory)

    def download_source_posters(self,
                                media_server_id: int,
                                library_id: int,
                                cancel_check: Callable[[], bool] = None) -> int:
        with self._session() as session:
            if not self._collections_tracked(session, library_id):
                return 0
            pending = [c for c in self._collections(session, library_id)
                       if c.poster_url and not c.processed
                       and not self._file_store.exists(library_id, c.id)]

        if not pending:
            return 0

        logger.info("Downloading %d collection posters for library %s", len(pending), library_id)
        downloaded = self._each(pending, cancel_check,
                                lambda collection: self._download_one(library_id, collection))
        self._announce(media_server_id, library_id, downloaded)
        return downloaded

    def _download_one(self, library_id: int, collection: LibraryCollection) -> bool:
        try:
            self._file_store.save(library_id, collection.id, fetch_as_jpeg(collection.poster_url))
            return True
        except Exception:
            logger.warning("[collection-download] %s (%s): FAILED",
                           collection.id, collection.title, exc_info=True)
            return False

    def generate_library_collection_posters(self,
                                            media_server_id: int,
                                            library_id: int,
                                            cancel_check: Callable[[], bool] = None,
                                            upload: Optional[bool] = None) -> int:
        with self._session() as session:
            settings = LibrarySettingsService(session).get_settings_or_default(library_id)
            if not settings.track_collections:
                return 0
            style = resolve_library_style(session, library_id)
            pending = [c for c in self._collections(session, library_id) if not c.locked]

        if not pending:
            return 0

        logger.info("Generating %d collection posters for library %s", len(pending), library_id)
        generated = self._each(pending, cancel_check,
                               lambda collection: self.generate_one(
                                   library_id, collection, style,
                                   media_server_id=media_server_id,
                                   upload=(settings.upload_enabled if upload is None else upload)))
        self._announce(media_server_id, library_id, generated)
        return generated

    def generate_one(self,
                     library_id: int,
                     collection: LibraryCollection,
                     style,
                     media_server_id: Optional[int] = None,
                     upload: bool = False) -> bool:
        catalogue = self._catalogue_poster(library_id, collection)
        source = catalogue or self._source_for(library_id, collection)
        if source is None:
            return False
        return self._store(library_id, collection, source,
                           title=collection.title,
                           overlay_options=style.overlay_options,
                           text_options=style.text_options,
                           provider=TMDB_PROVIDER if catalogue else COLLECTION_PROVIDER,
                           media_server_id=media_server_id,
                           upload=upload)

    def _catalogue_poster(self, library_id: int, collection: LibraryCollection) -> Optional[str]:
        if self._aggregator_factory is None or collection.tmdb_collection_id is None:
            return None

        try:
            collection_id = collection.tmdb_collection_id

            with self._session() as session:
                posters = self._aggregator_factory(session).get_all_collection_posters(
                    collection_id)
            return posters[0].url if posters else None
        except Exception:
            logger.warning("Could not read catalogue posters for collection %s", collection.id,
                           exc_info=True)
            return None

    def resolve_collection_ids(self,
                               media_server_id: int,
                               library_id: int,
                               cancel_check: Callable[[], bool] = None) -> int:
        if self._aggregator_factory is None:
            return 0

        with self._session() as session:
            pending = [c for c in self._collections(session, library_id)
                       if c.tmdb_collection_id is None]

        if not pending:
            return 0

        logger.info("Resolving catalogue ids for %d collections in library %s",
                    len(pending), library_id)
        resolved = self._each(pending, cancel_check,
                              lambda collection: self._resolve_one(library_id, collection))
        if resolved:
            event_manager.publish_library_synced(media_server_id, library_id)
        return resolved

    def _resolve_one(self, library_id: int, collection: LibraryCollection) -> bool:
        try:
            resolved = self._lookup_collection_id(library_id, collection)
        except Exception:
            logger.warning("Could not resolve the catalogue id for collection %s", collection.id,
                           exc_info=True)
            return False

        if resolved is None:
            return False
        self._remember_collection_id(collection, resolved)
        return True

    def _lookup_collection_id(self, library_id: int,
                              collection: LibraryCollection) -> Optional[int]:
        with self._session() as session:
            member_ids = LibraryCollectionRepository(session).member_ids(collection.id)
            if not member_ids:
                return None
            members = LibraryRepository(session).find_items(
                LibraryItemSearch(library_id=library_id, item_ids=member_ids))
            tmdb_ids = [int(m.tmdb_id) for m in members if m.tmdb_id]
            if not tmdb_ids:
                return None
            return self._aggregator_factory(session).find_collection_id(tmdb_ids)

    def _remember_collection_id(self, collection: LibraryCollection, collection_id: int) -> None:
        try:
            with self._session() as session:
                stored = LibraryCollectionRepository(session).get_collection(
                    collection.library_id, collection.id)
                stored.tmdb_collection_id = collection_id
                LibraryCollectionRepository(session).create_or_update(stored)
                session.commit()
            collection.tmdb_collection_id = collection_id
        except Exception:
            logger.warning("Could not store the catalogue id for collection %s", collection.id,
                           exc_info=True)

    def apply_poster(self,
                     media_server_id: int,
                     library_id: int,
                     collection_id: int,
                     poster_source: str,
                     jpeg_quality: Optional[int] = None,
                     title: Optional[str] = None,
                     overlay_options=None,
                     text_options=None,
                     upload: Optional[bool] = None) -> bool:
        with self._session() as session:
            collection = LibraryCollectionRepository(session).get_collection(library_id,
                                                                             collection_id)
            style = resolve_library_style(session, library_id)
            if upload is None:
                upload = LibrarySettingsService(session).get_settings_or_default(
                    library_id).upload_enabled

        stored = self._store(
            library_id, collection, poster_source,
            title=title or collection.title,
            jpeg_quality=jpeg_quality,
            overlay_options=overlay_options if overlay_options is not None else style.overlay_options,
            text_options=text_options if text_options is not None else style.text_options,
            provider=MANUAL_PROVIDER,
            media_server_id=media_server_id,
            upload=upload,
        )
        self._announce(media_server_id, library_id, int(stored))
        return stored

    def _store(self,
               library_id: int,
               collection: LibraryCollection,
               source,
               title: str,
               provider: str,
               jpeg_quality: Optional[int] = None,
               overlay_options=None,
               text_options=None,
               media_server_id: Optional[int] = None,
               upload: bool = False) -> bool:
        try:
            poster_bytes = self._decorator.decorate_poster(
                source, title,
                jpeg_quality=jpeg_quality,
                overlay_options=overlay_options,
                text_options=text_options,
            )
            if not poster_bytes:
                return False

            if not collection.processed:
                self._file_store.preserve_source(library_id, collection.id)
            self._file_store.save(library_id, collection.id, poster_bytes)

            uploaded = upload and self._push(media_server_id, library_id, collection)

            with self._session() as session:
                repository = LibraryCollectionRepository(session)
                repository.update_collections([collection.id], CollectionPosterState(
                    processed=True,
                    poster_hash=collection.poster_hash,
                    poster_uploaded_at=collection.poster_uploaded_at if uploaded else None,
                ))
                ProviderStatsService(session).record(provider, library_id)
                session.commit()

            logger.info("[collection-poster] %s (%s): SUCCESS via %s",
                        collection.id, collection.title, provider)
            return True
        except Exception:
            logger.warning("[collection-poster] %s (%s): FAILED via %s",
                           collection.id, collection.title, provider, exc_info=True)
            return False

    def upload_library_collection_posters(self,
                                          media_server_id: int,
                                          library_id: int,
                                          cancel_check: Callable[[], bool] = None) -> int:
        if self._connector_factory is None:
            return 0

        with self._session() as session:
            if not self._collections_tracked(session, library_id):
                return 0
            pending = [c for c in self._collections(session, library_id)
                       if c.processed and self._file_store.exists(library_id, c.id)]

        if not pending:
            return 0

        logger.info("Uploading %d collection posters for library %s", len(pending), library_id)
        connector = self._connector_factory.get(media_server_id)
        return self._each(pending, cancel_check,
                          lambda collection: self._upload_one(library_id, collection, connector))

    def _upload_one(self, library_id: int, collection: LibraryCollection, connector) -> bool:
        if not self._uploader.upload_collection_if_changed(
                collection,
                str(self._file_store.path(library_id, collection.id)),
                self._file_store.digest(library_id, collection.id),
                connector):
            return False

        with self._session() as session:
            LibraryCollectionRepository(session).update_collections(
                [collection.id], CollectionPosterState(
                    poster_hash=collection.poster_hash,
                    poster_uploaded_at=collection.poster_uploaded_at))
        return True

    def _push(self,
              media_server_id: Optional[int],
              library_id: int,
              collection: LibraryCollection) -> bool:
        if self._connector_factory is None or media_server_id is None:
            return False
        try:
            return self._uploader.upload_collection_if_changed(
                collection,
                str(self._file_store.path(library_id, collection.id)),
                self._file_store.digest(library_id, collection.id),
                self._connector_factory.get(media_server_id))
        except Exception:
            logger.warning("[collection-upload] %s (%s): FAILED",
                           collection.id, collection.title, exc_info=True)
            return False

    def _source_for(self, library_id: int,
                    collection: LibraryCollection) -> Optional[Union[str, bytes]]:
        if self._file_store.source_version(library_id, collection.id) is not None:
            return self._file_store.fetch_source(library_id, collection.id)
        if self._file_store.exists(library_id, collection.id):
            return self._file_store.fetch(library_id, collection.id)
        return collection.poster_url or None

    @staticmethod
    def _announce(media_server_id: int, library_id: int, written: int) -> None:
        if written:
            event_manager.publish_library_synced(media_server_id, library_id)

    @staticmethod
    def _collections_tracked(session: Session, library_id: int) -> bool:
        return LibrarySettingsService(session).get_settings_or_default(library_id).track_collections

    @staticmethod
    def _collections(session: Session, library_id: int) -> List[LibraryCollection]:
        return LibraryCollectionRepository(session).find_collections(
            LibraryCollectionSearch(library_id=library_id))

    def _each(self,
              collections: List[LibraryCollection],
              cancel_check: Callable[[], bool],
              work: Callable[[LibraryCollection], bool]) -> int:
        done = 0
        total = len(collections)
        succeeded = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(work, c): c for c in collections}
            for future in as_completed(futures):
                if cancel_check and cancel_check():
                    executor.shutdown(wait=False, cancel_futures=True)
                    return succeeded
                collection = futures[future]
                try:
                    if future.result():
                        succeeded += 1
                except Exception:
                    logger.exception("[collections] %s (%s): FAILED (exception)",
                                     collection.id, collection.title)
                done += 1
                report_task_progress(done, total, "Collections")
        return succeeded

    def _session(self):
        return _closing(self._session_factory())

class _closing:

    def __init__(self, session: Session):
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, *exc_info) -> None:
        self._session.close()
