import logging

from affiche.app.mediaserver.library.model import LibrarySearch
from affiche.app.asynch.async_task_service import progress_segment, report_task_progress
from affiche.app.events import event_manager
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.config.database import SessionLocal
from affiche.config.dependencies import container

logger = logging.getLogger(__name__)

GENERATE_SYNC_FRACTION = 0.25

def sync_libraries_task(media_server_id: int,
                        cancel_check=None):
    session = SessionLocal()
    try:
        service = container.media_server_synchronisation_service(session)
        service.sync_libraries(media_server_id, cancel_check=cancel_check)
        session.commit()
    finally:
        session.close()

    event_manager.publish_library_synced(media_server_id)

    container.source_poster_service().download_source_posters(
        media_server_id, cancel_check=cancel_check
    )
    _download_collection_posters(media_server_id, cancel_check=cancel_check)
    report_task_progress(1, 1)

def sync_library_task(media_server_id: int,
                      library_id: int,
                      cancel_check=None,
                      incremental: bool = False):
    session = SessionLocal()
    try:
        service = container.media_server_synchronisation_service(session)
        service.sync_library(media_server_id, library_id, cancel_check=cancel_check,
                             incremental=incremental)
        session.commit()
    finally:
        session.close()

    event_manager.publish_library_synced(media_server_id, library_id)

    container.source_poster_service().download_source_posters(
        media_server_id, library_id, cancel_check=cancel_check
    )
    _download_collection_posters(media_server_id, library_id, cancel_check=cancel_check)
    report_task_progress(1, 1)

def _download_collection_posters(media_server_id: int,
                                 library_id: int = None,
                                 cancel_check=None) -> None:
    service = container.collection_poster_service()
    for library in _target_libraries(media_server_id, library_id):
        if cancel_check and cancel_check():
            return
        try:
            service.download_source_posters(media_server_id, library, cancel_check=cancel_check)
        except Exception:
            logger.exception("Collection poster download failed for library %s", library)

def _generate_collection_posters(media_server_id: int,
                                 library_id: int = None,
                                 cancel_check=None,
                                 upload: bool | None = None) -> None:
    service = container.collection_poster_service()
    for library in _target_libraries(media_server_id, library_id):
        if cancel_check and cancel_check():
            return
        try:
            service.generate_library_collection_posters(media_server_id, library,
                                                        cancel_check=cancel_check,
                                                        upload=upload)
        except Exception:
            logger.exception("Collection poster generation failed for library %s", library)

def _upload_collection_posters(media_server_id: int,
                               library_id: int = None,
                               cancel_check=None) -> None:
    service = container.collection_poster_service()
    for library in _target_libraries(media_server_id, library_id):
        if cancel_check and cancel_check():
            return
        try:
            service.upload_library_collection_posters(media_server_id, library,
                                                      cancel_check=cancel_check)
        except Exception:
            logger.exception("Collection poster upload failed for library %s", library)

def resolve_collection_ids_task(media_server_id: int, library_id: int, cancel_check=None):
    service = container.collection_poster_service()
    resolved = service.resolve_collection_ids(media_server_id, library_id,
                                              cancel_check=cancel_check)
    logger.info("Resolved %d collection ids in library %s", resolved, library_id)
    report_task_progress(1, 1)

def _target_libraries(media_server_id: int, library_id: int = None) -> list[int]:
    if library_id is not None:
        return [library_id]

    session = SessionLocal()
    try:
        return [library.id for library
                in LibraryRepository(session).find_libraries(
                    LibrarySearch(media_server_id=media_server_id, enabled=True))]
    except Exception:
        logger.exception("Could not list libraries for collection posters on server %s",
                         media_server_id)
        return []
    finally:
        session.close()

def sync_posters_task(media_server_id: int,
                      cancel_check=None):
    with progress_segment(0, GENERATE_SYNC_FRACTION):
        sync_libraries_task(media_server_id, cancel_check=cancel_check)
    if cancel_check and cancel_check():
        return

    with progress_segment(GENERATE_SYNC_FRACTION, 1 - GENERATE_SYNC_FRACTION):
        service = container.poster_sync_service()
        service.apply_posters_to_all_libraries(media_server_id=media_server_id,
                                               cancel_check=cancel_check)
        _generate_collection_posters(media_server_id, cancel_check=cancel_check)
    report_task_progress(1, 1)

def sync_library_posters_task(media_server_id: int, library_id: int, cancel_check=None,
                              upload: bool | None = None, incremental: bool = False):
    with progress_segment(0, GENERATE_SYNC_FRACTION):
        sync_library_task(media_server_id, library_id, cancel_check=cancel_check,
                          incremental=incremental)
    if cancel_check and cancel_check():
        return

    with progress_segment(GENERATE_SYNC_FRACTION, 1 - GENERATE_SYNC_FRACTION):
        service = container.poster_sync_service()
        service.apply_posters_to_library(media_server_id, library_id, cancel_check=cancel_check,
                                         upload=upload)
        _generate_collection_posters(media_server_id, library_id, cancel_check=cancel_check,
                                     upload=upload)
    report_task_progress(1, 1)

def generate_items_task(media_server_id: int, item_ids: list[int], cancel_check=None):
    service = container.poster_sync_service()
    service.apply_posters_to_items(media_server_id, item_ids, cancel_check=cancel_check)

def reset_items_task(media_server_id: int, item_ids: list[int], cancel_check=None):
    service = container.poster_sync_service()
    service.reset_items_posters(media_server_id, item_ids, cancel_check=cancel_check)

def upload_items_task(media_server_id: int, item_ids: list[int], cancel_check=None):
    service = container.poster_sync_service()
    service.upload_items_posters(media_server_id, item_ids, cancel_check=cancel_check)

def reset_posters_task(media_server_id: int,
                       library_id: int | None = None,
                       cancel_check=None,
                       include_unprocessed: bool = False):
    service = container.poster_sync_service()
    service.reset_libraries_posters(media_server_id, library_id, cancel_check=cancel_check,
                                    include_unprocessed=include_unprocessed)

def upload_posters_task(media_server_id: int,
                        library_id: int | None = None,
                        cancel_check=None):
    service = container.poster_sync_service()
    service.upload_libraries_posters(media_server_id, library_id, cancel_check=cancel_check)
    _upload_collection_posters(media_server_id, library_id, cancel_check=cancel_check)
