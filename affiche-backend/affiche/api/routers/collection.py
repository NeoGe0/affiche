import logging
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from starlette import status

from affiche.api.schemas.library import (
    ApplyPosterRequest,
    LibraryItemResponse,
    SyncTaskResponse,
)
from affiche.app.asynch import library_tasks
from affiche.app.asynch.async_task_service import AsyncTaskService
from affiche.api.schemas.collection import (
    CollectionCreateRequest,
    CollectionLockRequest,
    CollectionMembersChanged,
    CollectionMembersRequest,
    CollectionRenameRequest,
    CollectionResponse,
    CollectionWithMembers,
    PaginatedCollections,
)
from affiche.app.mediaserver.library.collections.library_collection_service import (
    CollectionWriteError,
    LibraryCollectionService,
)
from affiche.app.mediaserver.library.collections.model.library_collection import (
    LibraryCollection,
    LibraryCollectionSearch,
)
from affiche.app.mediaserver.library import LibraryService
from affiche.app.mediaserver.library.model import SortDir
from affiche.config.dependencies import (
    container,
    get_async_task_service,
    get_library_collection_service,
    get_library_service,
)

router = APIRouter(prefix="/{media_server_id}/libraries/{library_id}/collections", tags=["Collection"])
logger = logging.getLogger(__name__)

class CollectionQuery:

    def __init__(self,
                 search: Optional[str] = None,
                 locked: Optional[bool] = None,
                 processed: Optional[bool] = None,
                 sort_by: str = 'title',
                 sort_dir: SortDir = SortDir.ASC,
                 page: int = Query(0, ge=0),
                 page_size: int = Query(50, ge=1)):
        self.search = search
        self.locked = locked
        self.processed = processed
        self.sort_by = sort_by
        self.sort_dir = sort_dir
        self.page = page
        self.page_size = page_size

    def to_domain(self, library_id: int) -> LibraryCollectionSearch:
        return LibraryCollectionSearch(
            library_id=library_id, search=self.search, locked=self.locked,
            processed=self.processed, sort_by=self.sort_by, sort_dir=self.sort_dir,
            page=self.page, page_size=self.page_size,
        )

@router.get("", response_model=PaginatedCollections)
def get_collections(media_server_id: int,
                    library_id: int,
                    query: Annotated[CollectionQuery, Depends()],
                    library_service: LibraryService = Depends(get_library_service),
                    service: LibraryCollectionService = Depends(get_library_collection_service)
                    ) -> PaginatedCollections:
    library_service.get_library(media_server_id, library_id)

    search = query.to_domain(library_id)
    collections = service.find_collections(search)
    counts = service.member_counts(collections)
    return PaginatedCollections(
        collections=[_collection_response(library_id, c, counts.get(c.id, 0)) for c in collections],
        total=service.count_collections(search),
        page=search.page,
        page_size=query.page_size,
    )

@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(media_server_id: int,
                      library_id: int,
                      request: CollectionCreateRequest,
                      service: LibraryCollectionService = Depends(get_library_collection_service)
                      ) -> CollectionResponse:
    collection = _write(lambda: service.create_collection(
        media_server_id, library_id, request.title, request.item_ids))
    return _collection_response(library_id, collection, len(request.item_ids))

@router.get("/{collection_id}", response_model=CollectionWithMembers)
def get_collection(media_server_id: int,
                   library_id: int,
                   collection_id: int,
                   service: LibraryCollectionService = Depends(get_library_collection_service)
                   ) -> CollectionWithMembers:
    collection = service.get_collection(media_server_id, library_id, collection_id)
    members = service.get_members(media_server_id, library_id, collection_id)
    base = _collection_response(library_id, collection, len(members))
    return CollectionWithMembers(
        **base.model_dump(),
        members=[LibraryItemResponse.of(library_id, item, container.file_store)
                 for item in members],
    )

@router.patch("/{collection_id}", response_model=CollectionResponse)
def rename_collection(media_server_id: int,
                      library_id: int,
                      collection_id: int,
                      request: CollectionRenameRequest,
                      service: LibraryCollectionService = Depends(get_library_collection_service)
                      ) -> CollectionResponse:
    collection = _write(lambda: service.rename_collection(
        media_server_id, library_id, collection_id, request.title))
    return _collection_response(library_id, collection, 0)

@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(media_server_id: int,
                      library_id: int,
                      collection_id: int,
                      service: LibraryCollectionService = Depends(get_library_collection_service)):
    _write(lambda: service.delete_collection(media_server_id, library_id, collection_id))

@router.post("/{collection_id}/items", response_model=CollectionMembersChanged)
def add_collection_items(media_server_id: int,
                         library_id: int,
                         collection_id: int,
                         request: CollectionMembersRequest,
                         service: LibraryCollectionService = Depends(get_library_collection_service)
                         ) -> CollectionMembersChanged:
    changed = _write(lambda: service.add_items(
        media_server_id, library_id, collection_id, request.item_ids))
    return CollectionMembersChanged(changed=changed)

@router.post("/{collection_id}/items/remove", response_model=CollectionMembersChanged)
def remove_collection_items(media_server_id: int,
                            library_id: int,
                            collection_id: int,
                            request: CollectionMembersRequest,
                            service: LibraryCollectionService = Depends(get_library_collection_service)
                            ) -> CollectionMembersChanged:
    changed = _write(lambda: service.remove_items(
        media_server_id, library_id, collection_id, request.item_ids))
    return CollectionMembersChanged(changed=changed)

@router.put("/{collection_id}/lock", response_model=CollectionResponse)
def set_collection_lock(media_server_id: int,
                        library_id: int,
                        collection_id: int,
                        request: CollectionLockRequest,
                        service: LibraryCollectionService = Depends(get_library_collection_service)
                        ) -> CollectionResponse:
    collection = service.set_locked(media_server_id, library_id, collection_id, request.locked)
    return _collection_response(library_id, collection, 0)

@router.post("/resolve", response_model=SyncTaskResponse)
def resolve_collection_ids(media_server_id: int,
                           library_id: int,
                           background_tasks: BackgroundTasks,
                           library_service: LibraryService = Depends(get_library_service),
                           task_service: AsyncTaskService = Depends(get_async_task_service)
                           ) -> SyncTaskResponse:
    library_service.get_library(media_server_id, library_id)

    task_id, task_status = task_service.submit_task(
        background_tasks=background_tasks,
        task_func=lambda cancel_check=None: library_tasks.resolve_collection_ids_task(
            media_server_id, library_id, cancel_check=cancel_check),
        task_name=f"collection_resolve_{library_id}",
        blocking=True,
        resource=f"ms:{media_server_id}:lib:{library_id}",
    )
    return SyncTaskResponse(
        status=task_status,
        task_id=task_id,
        message=f"Collection matching started for library {library_id}",
    )

@router.post("/{collection_id}/posters", status_code=status.HTTP_204_NO_CONTENT)
def apply_collection_poster(media_server_id: int,
                            library_id: int,
                            collection_id: int,
                            request: ApplyPosterRequest,
                            service: LibraryCollectionService = Depends(
                                get_library_collection_service)):
    service.get_collection(media_server_id, library_id, collection_id)

    overlay_options, text_options = request.style_overrides()
    poster_source = request.resolved_poster_source()

    applied = container.collection_poster_service().apply_poster(
        media_server_id, library_id, collection_id, poster_source,
        jpeg_quality=request.jpeg_quality, title=request.title,
        overlay_options=overlay_options, text_options=text_options,
        upload=request.upload)

    if not applied:
        raise HTTPException(status_code=502,
                            detail="The poster could not be applied to this collection")

def _write(action):
    try:
        return action()
    except CollectionWriteError as error:
        raise HTTPException(status_code=502, detail=error.message)

def _collection_response(library_id: int,
                         collection: LibraryCollection,
                         member_count: int) -> CollectionResponse:
    return CollectionResponse.of(library_id, collection, member_count,
                                 container.collection_file_store)
