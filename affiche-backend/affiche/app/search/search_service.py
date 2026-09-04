import logging
from typing import Dict

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.model import LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository
from affiche.app.search.model.search import (
    GlobalItemSearch,
    SearchHit,
    SearchResults,
    SearchScope,
)

logger = logging.getLogger(__name__)

class SearchService:

    def __init__(self, session: Session):
        self._library_repo = LibraryRepository(session)
        self._media_server_repo = MediaServerRepository(session)

    def search_items(self, query: GlobalItemSearch) -> SearchResults:
        scopes = self._scopes()
        if not scopes:
            return SearchResults(hits=[], total=0)

        search = LibraryItemSearch(
            library_ids=list(scopes),
            search=query.search,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
            page=query.page,
            page_size=query.page_size,
        )
        items = self._library_repo.find_items(search)
        return SearchResults(
            hits=[SearchHit(item=item, scope=scopes[item.library_id]) for item in items],
            total=self._library_repo.count_items(search),
        )

    def _scopes(self) -> Dict[int, SearchScope]:
        return {
            library.id: SearchScope(
                library_id=library.id,
                library_name=library.name,
                library_type=library.type,
                media_server_id=server.id,
                media_server_name=server.name,
                media_server_type=server.type,
            )
            for server in self._media_server_repo.find_all()
            for library in self._library_repo.find_libraries(
                LibrarySearch(media_server_id=server.id))
        }
