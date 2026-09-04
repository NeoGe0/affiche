from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from affiche.app.mediaserver.library.model import LibraryItem, SearchCriteria

class GlobalItemSearch(SearchCriteria):
    search: Optional[str] = None

class SearchScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    library_id: int
    library_name: str
    library_type: str
    media_server_id: int
    media_server_name: str
    media_server_type: str

class SearchHit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    item: LibraryItem
    scope: SearchScope

class SearchResults(BaseModel):
    hits: List[SearchHit]
    total: int
