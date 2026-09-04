from typing import List

from pydantic import BaseModel, Field

from affiche.api.schemas.library import LibraryItemResponse

class SearchHitResponse(LibraryItemResponse):
    library_name: str
    library_type: str
    media_server_id: int
    media_server_name: str
    media_server_type: str

class SearchResponse(BaseModel):
    items: List[SearchHitResponse]
    total: int
    total_pages: int
    page: int
    page_size: int

    @classmethod
    def of(cls, items: List[SearchHitResponse], total: int, page: int,
           page_size: int) -> 'SearchResponse':
        return cls(
            items=items,
            total=total,
            total_pages=-(-total // page_size),
            page=page,
            page_size=page_size,
        )

class SearchQuery(BaseModel):
    search: str = Field(min_length=1)
    page: int = Field(0, ge=0)
    page_size: int = Field(25, ge=1, le=100)
