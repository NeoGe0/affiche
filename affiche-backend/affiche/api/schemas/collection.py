from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from affiche.api.schemas.library import LibraryItemResponse
from affiche.app.filestore.filestore import FileStoreService

class CollectionResponse(BaseModel):
    id: int
    library_id: int
    external_id: Optional[str] = None
    title: str
    sort_title: Optional[str] = None
    child_count: Optional[int] = None
    member_count: int = 0
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    poster_uploaded_at: Optional[datetime] = None
    poster_provider: Optional[str] = None
    tmdb_collection_id: Optional[int] = None
    processed: bool = False
    locked: bool = False
    error_message: Optional[str] = None
    has_poster: bool = False
    poster_version: Optional[str] = None
    source_poster_version: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def of(cls, library_id: int, collection, member_count: int,
           store: FileStoreService) -> "CollectionResponse":
        resp = cls.model_validate(collection)
        resp.member_count = member_count
        resp.poster_version = store.version(library_id, collection.id)
        resp.has_poster = resp.poster_version is not None
        resp.source_poster_version = store.source_version(library_id, collection.id)
        return resp

class PaginatedCollections(BaseModel):
    collections: List[CollectionResponse]
    total: int
    page: int
    page_size: int

class CollectionWithMembers(CollectionResponse):
    members: List[LibraryItemResponse] = []

class CollectionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=1024)
    item_ids: List[int] = Field(..., min_length=1)

class CollectionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=1024)

class CollectionMembersRequest(BaseModel):
    item_ids: List[int] = Field(..., min_length=1)

class CollectionLockRequest(BaseModel):
    locked: bool

class CollectionMembersChanged(BaseModel):
    changed: int
