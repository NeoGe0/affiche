import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from starlette import status

from affiche.api.schemas.library import (
    Library,
    LibraryItemResponse,
    SyncTaskResponse,
    LibraryItemWithSeasons,
    ItemSeason,
    ItemEpisode,
    PaginatedLibraryItems,
    AlphaIndexEntry,
    LibraryItemCounts,
    LibraryItemQuery,
    LibraryStyleStaleness,
    ApplyPosterRequest,
    BulkLockResponse,
    ItemLockRequest,
    ItemSelectionLockRequest,
    ItemSelectionRequest,
    TrashEmptyResponse,
)
from affiche.api.schemas.library_settings import LibrarySettingsResponse, LibrarySettingsUpdate
from affiche.app.asynch import library_tasks
from affiche.app.asynch.async_task_service import AsyncTaskService
from affiche.app.events import event_manager
from affiche.app.mediaserver.library import LibraryService
from affiche.app.mediaserver.library.model.library import Library as LibraryModel
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.mediaserver.library.sync.media_server_synchronisation_service import (
    MediaServerSynchronisationService,
)
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService

from affiche.config.dependencies import (
    require_admin,
    container,
    get_async_task_service,
    get_library_service,
    get_library_settings_service,
    get_media_server_synchronisation_service,
    get_poster_sync_service,
)

from affiche.app.mediaserver.library.model import (
    NO_PROVIDER,
    LibraryItemSearch,
    LibrarySearch,
    SortDir,
)

router = APIRouter(prefix="/{media_server_id}/libraries", tags=["Library"])
logger = logging.getLogger(__name__)

@router.get("", response_model=List[Library])
def get_libraries(media_server_id: int,
                        enabled: Optional[bool] = None,
                        service: LibraryService = Depends(get_library_service)) -> List[Library]:
    libraries = service.find_libraries(LibrarySearch(media_server_id=media_server_id, enabled=enabled))
    counts = service.count_items_per_library(
        LibraryItemSearch(library_ids=[lib.id for lib in libraries]))
    return [_db_library_to_response(lib, counts.get(lib.id, 0)) for lib in libraries]

@router.post("/posters/sync", response_model=SyncTaskResponse)
def sync_all_posters(media_server_id: int,
                           background_tasks: BackgroundTasks,
                           task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.sync_posters_task(media_server_id, cancel_check),
        task_name="poster_sync",
        blocking=True,
        resource=f"ms:{media_server_id}:*",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message="Poster sync started for all libraries",
    )

@router.post("/posters/reset", response_model=SyncTaskResponse)
def reset_all_posters(media_server_id: int,
                            background_tasks: BackgroundTasks,
                            include_unprocessed: bool = False,
                            task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.reset_posters_task(
            media_server_id, cancel_check=cancel_check, include_unprocessed=include_unprocessed),
        task_name="poster_reset",
        blocking=True,
        resource=f"ms:{media_server_id}:*",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message="Poster reset started for all libraries",
    )

@router.post("/items/selection/posters/generate", response_model=SyncTaskResponse)
def generate_selected_posters(media_server_id: int,
                              request: ItemSelectionRequest,
                              background_tasks: BackgroundTasks,
                              task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    item_ids = request.item_ids
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.generate_items_task(
            media_server_id, item_ids, cancel_check=cancel_check),
        task_name=f"poster_sync_selection_{media_server_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:*",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Poster generation started for {len(item_ids)} item(s)",
    )

@router.post("/items/selection/posters/upload", response_model=SyncTaskResponse)
def upload_selected_posters(media_server_id: int,
                            request: ItemSelectionRequest,
                            background_tasks: BackgroundTasks,
                            task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    item_ids = request.item_ids
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.upload_items_task(
            media_server_id, item_ids, cancel_check=cancel_check),
        task_name=f"poster_upload_selection_{media_server_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:*",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Poster upload started for {len(item_ids)} item(s)",
    )

@router.post("/items/selection/posters/reset", response_model=SyncTaskResponse)
def reset_selected_posters(media_server_id: int,
                           request: ItemSelectionRequest,
                           background_tasks: BackgroundTasks,
                           task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    item_ids = request.item_ids
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.reset_items_task(
            media_server_id, item_ids, cancel_check=cancel_check),
        task_name=f"poster_reset_selection_{media_server_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:*",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Poster reset started for {len(item_ids)} item(s)",
    )

@router.put("/items/selection/lock", response_model=BulkLockResponse)
def set_selected_items_lock(media_server_id: int,
                            request: ItemSelectionLockRequest,
                            service: LibraryService = Depends(get_library_service)) -> BulkLockResponse:
    changed = service.set_items_locked(media_server_id, request.item_ids, request.locked)
    return BulkLockResponse(changed=changed)

@router.get("/{library_id}", response_model=Library)
def get_library(media_server_id: int,
                      library_id: int,
                      service: LibraryService = Depends(get_library_service)) -> Library:
    library = service.get_library(media_server_id, library_id)
    return _db_library_to_response(library, None)

@router.delete("/{library_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_library(media_server_id: int,
                         library_id: int,
                         service: LibraryService = Depends(get_library_service)):
    if not service.delete_library(media_server_id, library_id):
        raise HTTPException(404, f"Library {library_id} not found")

@router.get("/{library_id}/items", response_model=PaginatedLibraryItems)
def get_library_items(media_server_id: int,
                      library_id: int,
                      query: Annotated[LibraryItemQuery, Query()],
                      service: LibraryService = Depends(get_library_service)) -> PaginatedLibraryItems:
    service.get_library(media_server_id, library_id)

    search = query.to_domain(library_id)
    return PaginatedLibraryItems.of(
        items=[_item_response(library_id, item) for item in service.find_items(search)],
        total=service.count_items(search),
        search=search,
        page_size=query.page_size,
    )

@router.get("/{library_id}/items/counts", response_model=LibraryItemCounts)
def get_library_item_counts(media_server_id: int,
                            library_id: int,
                            query: Annotated[LibraryItemQuery, Query()],
                            service: LibraryService = Depends(get_library_service)) -> LibraryItemCounts:
    service.get_library(media_server_id, library_id)

    stats = service.count_status_buckets(query.to_domain(library_id, status=None))
    providers = service.count_items_by_provider(query.to_domain(library_id, provider=None))
    return LibraryItemCounts(
        total=stats.total, unprocessed=stats.unprocessed,
        errors=stats.errors, locked=stats.locked,
        providers={(provider or NO_PROVIDER): count for provider, count in providers.items()},
    )

@router.get("/{library_id}/items/alpha-index", response_model=List[AlphaIndexEntry])
def get_library_alpha_index(media_server_id: int,
                            library_id: int,
                            query: Annotated[LibraryItemQuery, Query()],
                            service: LibraryService = Depends(get_library_service)) -> List[AlphaIndexEntry]:
    service.get_library(media_server_id, library_id)
    if query.sort_by != 'title' or query.sort_dir is not SortDir.ASC:
        raise HTTPException(400, "The alphabet index is only defined for a title-ascending listing")

    search = query.to_domain(library_id)
    return [AlphaIndexEntry(letter=letter, page=offset // query.page_size)
            for letter, offset in service.letter_offsets(search)]

@router.get("/{library_id}/trash", response_model=PaginatedLibraryItems)
def get_library_trash(media_server_id: int,
                      library_id: int,
                      query: Annotated[LibraryItemQuery, Query()],
                      service: LibraryService = Depends(get_library_service)) -> PaginatedLibraryItems:
    service.get_library(media_server_id, library_id)

    search = query.to_domain(library_id, deleted=True, status=None,
                             sort_by='deleted_at', sort_dir=SortDir.DESC)
    return PaginatedLibraryItems.of(
        items=[_item_response(library_id, item) for item in service.find_items(search)],
        total=service.count_items(search),
        search=search,
        page_size=query.page_size,
    )

@router.post("/{library_id}/items/{item_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def restore_library_item(media_server_id: int,
                         library_id: int,
                         item_id: int,
                         service: LibraryService = Depends(get_library_service)):
    if service.restore_item(media_server_id, library_id, item_id) is None:
        raise HTTPException(404, f"Item {item_id} not found in trash")

@router.put("/{library_id}/items/{item_id}/lock", response_model=LibraryItemResponse)
def set_library_item_lock(media_server_id: int,
                          library_id: int,
                          item_id: int,
                          request: ItemLockRequest,
                          service: LibraryService = Depends(get_library_service)) -> LibraryItemResponse:
    item = service.set_item_locked(media_server_id, library_id, item_id, request.locked)
    return _item_response(library_id, item)

@router.post("/{library_id}/trash/empty", response_model=TrashEmptyResponse)
def empty_library_trash(media_server_id: int,
                        library_id: int,
                        service: LibraryService = Depends(get_library_service)) -> TrashEmptyResponse:
    service.get_library(media_server_id, library_id)

    purged = service.purge_deleted_items(library_id=library_id)
    event_manager.publish_library_synced(media_server_id, library_id)
    return TrashEmptyResponse(purged=purged)

def _library_settings_response(settings, enabled: bool) -> LibrarySettingsResponse:
    return LibrarySettingsResponse(
        library_id=settings.library_id,
        enabled=enabled,
        upload_enabled=settings.upload_enabled,
        provider_order=settings.provider_order,
        overlay_options=settings.overlay_options,
        text_options=settings.text_options,
        style_profile_id=settings.style_profile_id,
        track_episodes=settings.track_episodes,
        track_collections=settings.track_collections,
        auto_sync_enabled=settings.auto_sync_enabled,
        auto_sync_interval_minutes=settings.auto_sync_interval_minutes,
        auto_pickup_action=settings.auto_pickup_action,
        last_auto_sync_at=settings.last_auto_sync_at,
        last_full_sync_at=settings.last_full_sync_at,
    )

@router.get("/{library_id}/style-staleness", response_model=LibraryStyleStaleness)
def get_library_style_staleness(media_server_id: int,
                                library_id: int,
                                library_service: LibraryService = Depends(get_library_service),
                                service: LibraryPosterService = Depends(get_poster_sync_service)
                                ) -> LibraryStyleStaleness:
    library_service.get_library(media_server_id, library_id)

    staleness = service.get_style_staleness(library_id)
    return LibraryStyleStaleness(stale=staleness.stale, total=staleness.total)

@router.get("/{library_id}/settings", response_model=LibrarySettingsResponse)
def get_library_settings(media_server_id: int,
                               library_id: int,
                               service: LibrarySettingsService = Depends(get_library_settings_service)) -> LibrarySettingsResponse:
    settings = service.get_settings_or_default(library_id)
    return _library_settings_response(settings, service.is_enabled(media_server_id, library_id))

@router.patch("/{library_id}/settings", response_model=LibrarySettingsResponse,
              dependencies=[Depends(require_admin)])
def update_library_settings(media_server_id: int,
                                  library_id: int,
                                  update: LibrarySettingsUpdate,
                                  service: LibrarySettingsService = Depends(get_library_settings_service)) -> LibrarySettingsResponse:

    updates = update.model_dump(exclude_unset=True)
    enabled_update = updates.pop("enabled", None)
    settings = service.partial_update_settings(library_id, updates)
    enabled = (service.set_enabled(media_server_id, library_id, enabled_update)
               if enabled_update is not None
               else service.is_enabled(media_server_id, library_id))
    return _library_settings_response(settings, enabled)

@router.post("/sync", response_model=SyncTaskResponse)
def sync_all_libraries(media_server_id: int,
                             background_tasks: BackgroundTasks,
                             task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:

    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.sync_libraries_task(media_server_id, cancel_check),
        task_name=f"library_sync_{media_server_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:*",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message="Library sync started",
    )

@router.post("/{library_id}/sync", response_model=SyncTaskResponse)
def sync_library(media_server_id: int,
                       library_id: int,
                       background_tasks: BackgroundTasks,
                       task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    task_id, task_status = task_service.submit_task(background_tasks=background_tasks,
                                                    task_func=lambda cancel_check=None: library_tasks.sync_library_task(
                                                        media_server_id, library_id, cancel_check),
                                                    task_name=f"library_sync_{media_server_id}_{library_id}",
                                                    blocking=True,
                                                    resource=f"ms:{media_server_id}:lib:{library_id}",
                                                    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Sync started for library {library_id}",
    )

@router.post("/{library_id}/posters/sync", response_model=SyncTaskResponse)
def sync_library_posters(media_server_id: int,
                               library_id: int,
                               background_tasks: BackgroundTasks,
                               task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.sync_library_posters_task(media_server_id, library_id, cancel_check),
        task_name=f"poster_sync_{library_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:lib:{library_id}",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Poster sync started for library {library_id}",
    )

@router.post("/{library_id}/items/{item_id}/sync", response_model=LibraryItemResponse)
def sync_library_item(media_server_id: int,
                      library_id: int,
                      item_id: int,
                      service: MediaServerSynchronisationService = Depends(
                          get_media_server_synchronisation_service)) -> LibraryItemResponse:
    item = service.sync_item(media_server_id, library_id, item_id)
    return _item_response(library_id, item)

@router.post("/{library_id}/items/{item_id}/posters/sync", status_code=status.HTTP_204_NO_CONTENT)
def sync_library_item_posters(media_server_id: int,
                                    library_id: int,
                                    item_id: int,
                                    service: LibraryPosterService = Depends(get_poster_sync_service)):
    service.apply_item_posters(media_server_id, library_id, item_id)

@router.post("/{library_id}/posters/reset", response_model=SyncTaskResponse)
def reset_library_posters(media_server_id: int,
                                library_id: int,
                                background_tasks: BackgroundTasks,
                                include_unprocessed: bool = False,
                                task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.reset_posters_task(
            media_server_id, library_id, cancel_check=cancel_check, include_unprocessed=include_unprocessed),
        task_name=f"poster_reset_{library_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:lib:{library_id}",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Poster reset started for library {library_id}",
    )

@router.post("/{library_id}/items/{item_id}/posters/reset", response_model=LibraryItemResponse)
def reset_library_item_posters(media_server_id: int,
                                     library_id: int,
                                     item_id: int,
                                     service: LibraryPosterService = Depends(get_poster_sync_service),
                                     library_service: LibraryService = Depends(get_library_service)) -> LibraryItemResponse:
    service.reset_item_posters(media_server_id, library_id, item_id)
    item = library_service.get_library_item(media_server_id, library_id, item_id)
    return _item_response(library_id, item)

@router.post("/posters/upload", response_model=SyncTaskResponse)
def upload_all_posters(media_server_id: int,
                       background_tasks: BackgroundTasks,
                       task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.upload_posters_task(media_server_id, cancel_check=cancel_check),
        task_name=f"poster_upload_{media_server_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:*",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message="Poster upload started",
    )

@router.post("/{library_id}/posters/upload", response_model=SyncTaskResponse)
def upload_library_posters(media_server_id: int,
                           library_id: int,
                           background_tasks: BackgroundTasks,
                           task_service: AsyncTaskService = Depends(get_async_task_service)) -> SyncTaskResponse:
    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.upload_posters_task(
            media_server_id, library_id, cancel_check=cancel_check),
        task_name=f"poster_upload_{library_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:lib:{library_id}",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Poster upload started for library {library_id}",
    )

@router.post("/{library_id}/items/{item_id}/posters/upload", status_code=status.HTTP_204_NO_CONTENT)
def upload_library_item_poster(media_server_id: int,
                               library_id: int,
                               item_id: int,
                               service: LibraryPosterService = Depends(get_poster_sync_service)):
    service.upload_item_poster(media_server_id, library_id, item_id)

@router.post("/{library_id}/items/{item_id}/posters", status_code=status.HTTP_204_NO_CONTENT)
def apply_item_poster(media_server_id: int,
                            library_id: int,
                            item_id: int,
                            request: ApplyPosterRequest,
                            service: LibraryPosterService = Depends(get_poster_sync_service)):
    overlay_options, text_options = request.style_overrides()
    poster_source = request.resolved_poster_source()
    service.apply_poster(media_server_id, library_id, item_id, poster_source,
                         jpeg_quality=request.jpeg_quality, title=request.title,
                         overlay_options=overlay_options, text_options=text_options,
                         upload=request.upload)

@router.get("/{library_id}/items/{item_id}", response_model=LibraryItemResponse)
def get_library_item(media_server_id: int,
                     library_id: int,
                     item_id: int,
                     service: LibraryService = Depends(get_library_service)) -> LibraryItemResponse:
    return _item_response(library_id, service.get_library_item(media_server_id, library_id, item_id))

@router.get("/{library_id}/items/{item_id}/seasons", response_model=LibraryItemWithSeasons)
def get_item_with_seasons(media_server_id: int,
                                library_id: int,
                                item_id: int,
                                service: LibraryService = Depends(get_library_service)) -> LibraryItemWithSeasons:
    item = service.get_library_item(media_server_id, library_id, item_id)
    seasons = service.get_item_seasons(library_id, item_id)

    base = _item_response(library_id, item)
    return LibraryItemWithSeasons(
        **base.model_dump(),
        seasons=[_season_response(library_id, item_id, s) for s in seasons],
    )

@router.get("/{library_id}/items/{item_id}/seasons/{season_number}/episodes",
            response_model=List[ItemEpisode])
def get_season_episodes(media_server_id: int,
                        library_id: int,
                        item_id: int,
                        season_number: int,
                        service: LibraryService = Depends(get_library_service)) -> List[ItemEpisode]:
    service.get_library(media_server_id, library_id)
    episodes = service.get_season_episodes(library_id, item_id, season_number)
    return [ItemEpisode.model_validate(e) for e in episodes]

@router.post("/{library_id}/items/{item_id}/seasons/{season_number}/posters", status_code=status.HTTP_204_NO_CONTENT)
def apply_season_poster(media_server_id: int,
                              library_id: int,
                              item_id: int,
                              season_number: int,
                              request: ApplyPosterRequest,
                              service: LibraryPosterService = Depends(get_poster_sync_service)):
    overlay_options, text_options = request.style_overrides()
    poster_source = request.resolved_poster_source()
    service.apply_poster(media_server_id, library_id, item_id, poster_source, season_number,
                         jpeg_quality=request.jpeg_quality, title=request.title,
                         overlay_options=overlay_options, text_options=text_options,
                         upload=request.upload)

def _item_response(library_id: int, item) -> LibraryItemResponse:
    return LibraryItemResponse.of(library_id, item, container.file_store)

def _season_response(library_id: int, item_id: int, season) -> ItemSeason:
    return ItemSeason.of(library_id, item_id, season, container.file_store)

def _db_library_to_response(lib: LibraryModel, media_count: Optional[int]) -> Library:
    return Library(
        id=lib.id,
        media_server_id=lib.media_server_id,
        name=lib.name,
        library_type=lib.type,
        agent=lib.agent,
        scanner=getattr(lib, "scanner", None),
        language=lib.language,
        created_at=lib.created_at,
        updated_at=lib.updated_at,
        media_count=media_count,
        enabled=lib.enabled,
    )
