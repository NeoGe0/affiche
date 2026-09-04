from typing import Annotated

from fastapi import APIRouter, Depends, Query

from affiche.api.schemas.library import LibraryItemResponse
from affiche.api.schemas.search import SearchHitResponse, SearchQuery, SearchResponse
from affiche.app.search import GlobalItemSearch, SearchService
from affiche.config.dependencies import container, get_search_service

router = APIRouter()

@router.get("/items", response_model=SearchResponse)
def search_items(query: Annotated[SearchQuery, Query()],
                 service: SearchService = Depends(get_search_service)) -> SearchResponse:
    results = service.search_items(GlobalItemSearch(
        search=query.search, page=query.page, page_size=query.page_size))
    return SearchResponse.of(
        items=[_hit_response(hit) for hit in results.hits],
        total=results.total,
        page=query.page,
        page_size=query.page_size,
    )

def _hit_response(hit) -> SearchHitResponse:
    return SearchHitResponse(
        **LibraryItemResponse.of(hit.scope.library_id, hit.item, container.file_store).model_dump(),
        library_name=hit.scope.library_name,
        library_type=hit.scope.library_type,
        media_server_id=hit.scope.media_server_id,
        media_server_name=hit.scope.media_server_name,
        media_server_type=hit.scope.media_server_type,
    )
