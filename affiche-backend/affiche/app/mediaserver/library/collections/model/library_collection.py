from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from affiche.app.mediaserver.library.model.search_criteria import SearchCriteria

class LibraryCollection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    library_id: int
    external_id: str
    title: str
    sort_title: Optional[str] = None
    child_count: Optional[int] = None

    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    poster_uploaded_at: Optional[datetime] = None

    poster_url: Optional[str] = None
    poster_hash: Optional[str] = None
    poster_provider: Optional[str] = None
    tmdb_collection_id: Optional[int] = None

    processed: bool = False
    locked: bool = False
    error_message: Optional[str] = None

class LibraryCollectionSearch(SearchCriteria):

    library_id: Optional[int] = None
    library_ids: Optional[List[int]] = None
    collection_ids: Optional[List[int]] = None
    search: Optional[str] = None
    processed: Optional[bool] = None
    locked: Optional[bool] = None
    deleted: Optional[bool] = False

    @model_validator(mode='after')
    def _require_a_library_scope(self) -> 'LibraryCollectionSearch':
        if self.library_id is None and not self.library_ids:
            raise ValueError("a collection search must be scoped to a library")
        return self

class CollectionPosterState(BaseModel):
    model_config = ConfigDict(frozen=True)

    processed: Optional[bool] = None
    poster_hash: Optional[str] = None
    poster_uploaded_at: Optional[datetime] = None

    def changes(self) -> Dict[str, Any]:
        return self.model_dump(exclude_unset=True)
