from datetime import datetime
from typing import List, Mapping, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.connector.alchemy_library_connector import AlchemyLibraryConnector
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.model.library_item_search import LibraryItemSearch
from affiche.app.mediaserver.library.model.library_item_stats import LibraryItemStats
from affiche.config.exceptions.exceptions import LibraryNotFoundException, LibraryItemNotFoundException

class LibraryRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyLibraryConnector(session)

    def create_library(self, library: Library) -> Library:
        return self._connector.create_library(library)

    def get_library(self, media_server_id: int, library_id: int) -> Library:
        library = self._connector.find_library(media_server_id, library_id)
        if library is None:
            raise LibraryNotFoundException(library_id)
        return library

    def find_libraries(self, search: LibrarySearch) -> List[Library]:
        return self._connector.find_libraries(search)

    def set_library_enabled(self,
                            media_server_id: int,
                            library_id: int,
                            enabled: bool) -> Library:
        library = self._connector.set_library_enabled(media_server_id, library_id, enabled)
        if library is None:
            raise LibraryNotFoundException(library_id)
        return library

    def create_or_update_item(self, item: LibraryItem) -> LibraryItem:
        return self._connector.update_item(item)

    def create_or_update_items_batch(self, items: List[LibraryItem]) -> None:
        self._connector.create_or_update_items_batch(items)

    def find_items(self, search: LibraryItemSearch) -> List[LibraryItem]:
        return self._connector.find_items(search)

    def count_items(self, search: LibraryItemSearch) -> int:
        return self._connector.count_items(search)

    def count_items_per_library(self, search: LibraryItemSearch) -> dict[int, int]:
        return self._connector.count_items_per_library(search)

    def count_status_buckets(self, search: LibraryItemSearch) -> LibraryItemStats:
        return self._connector.count_status_buckets(search)

    def count_buckets_per_library(self, search: LibraryItemSearch) -> dict[int, LibraryItemStats]:
        return self._connector.count_buckets_per_library(search)

    def count_items_by_provider(self, search: LibraryItemSearch) -> dict[Optional[str], int]:
        return self._connector.count_items_by_provider(search)

    def count_posters_by_provider(self, search: LibraryItemSearch) -> dict[Optional[str], int]:
        return self._connector.count_posters_by_provider(search)

    def count_style_staleness(self, search: LibraryItemSearch, current_hash: str) -> tuple[int, int]:
        return self._connector.count_style_staleness(search, current_hash)

    def letter_offsets(self, search: LibraryItemSearch) -> List[tuple[str, int]]:
        return self._connector.letter_offsets(search)

    def get_library_item(self,
                         library_id,
                         item_id) -> LibraryItem:
        item = self._connector.get_library_item(library_id, item_id)
        if item is None:
            raise LibraryItemNotFoundException(item_id)
        return item

    def delete_library(self, media_server_id: int, library_id: int) -> bool:
        return self._connector.delete_library(media_server_id, library_id)

    def reconcile_deletions(self, library_id: int, seen_at: datetime) -> tuple[int, int]:
        return self._connector.reconcile_deletions(library_id, seen_at)

    def rekey_items(self, adoptions: Mapping[int, str]) -> int:
        return self._connector.rekey_items(adoptions)

    def restore_item(self, library_id: int, item_id: int) -> Optional[LibraryItem]:
        return self._connector.restore_item(library_id, item_id)

    def hard_delete_items(self, item_ids: List[int]) -> int:
        return self._connector.hard_delete_items(item_ids)
