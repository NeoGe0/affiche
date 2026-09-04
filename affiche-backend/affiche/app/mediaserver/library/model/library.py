from datetime import datetime
from typing import Optional

from pydantic import BaseModel, model_validator

from affiche.app.mediaserver.library.model.search_criteria import SearchCriteria

class Library(BaseModel):
    class Config:
        from_attributes = True

    id: Optional[int] = None
    media_server_id: int
    external_id: str
    name: str
    type: str
    agent: Optional[str] = None
    language: str
    uuid: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    enabled: bool

class LibrarySearch(SearchCriteria):
    media_server_id: Optional[int] = None
    enabled: Optional[bool] = None

    sort_by: str = 'name'

    @model_validator(mode='after')
    def _require_a_server_scope(self) -> 'LibrarySearch':
        if self.media_server_id is None:
            raise ValueError("a library search must be scoped to a media server")
        return self
