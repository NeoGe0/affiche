from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.collections.connector.alchemy_library_collection_connector import (
    AlchemyLibraryCollectionConnector,
)
from affiche.app.mediaserver.library.collections.model.library_collection import (
    CollectionPosterState,
    LibraryCollection,
    LibraryCollectionSearch,
)
from affiche.config.exceptions.exceptions import LibraryCollectionNotFoundException

class LibraryCollectionRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyLibraryCollectionConnector(session)

    def get_collection(self, library_id: int, collection_id: int) -> LibraryCollection:
        collection = self._connector.get_collection(library_id, collection_id)
        if collection is None:
            raise LibraryCollectionNotFoundException(collection_id)
        return collection

    def find_by_external_id(self, library_id: int, external_id: str) -> Optional[LibraryCollection]:
        return self._connector.find_by_external_id(library_id, external_id)

    def find_collections(self, search: LibraryCollectionSearch) -> List[LibraryCollection]:
        return self._connector.find_collections(search)

    def count_collections(self, search: LibraryCollectionSearch) -> int:
        return self._connector.count_collections(search)

    def create_or_update(self, collection: LibraryCollection) -> LibraryCollection:
        return self._connector.update_collection(collection)

    def create_or_update_batch(self, collections: List[LibraryCollection]) -> None:
        self._connector.create_or_update_batch(collections)

    def delete_collection(self, library_id: int, collection_id: int) -> bool:
        return self._connector.delete_collection(library_id, collection_id)

    def reconcile_deletions(self, library_id: int, seen_at: datetime) -> int:
        self._connector.restore_seen(library_id, seen_at)
        return self._connector.reconcile_deletions(library_id, seen_at)

    def update_collections(self, collection_ids: List[int],
                           state: CollectionPosterState) -> None:
        self._connector.update_collections(collection_ids, state)

    def set_members(self, collection_id: int, item_ids: List[int]) -> None:
        self._connector.set_members(collection_id, item_ids)

    def add_members(self, collection_id: int, item_ids: List[int]) -> None:
        self._connector.add_members(collection_id, item_ids)

    def remove_members(self, collection_id: int, item_ids: List[int]) -> None:
        self._connector.remove_members(collection_id, item_ids)

    def member_ids(self, collection_id: int) -> List[int]:
        return self._connector.member_ids(collection_id)

    def member_counts(self, collection_ids: List[int]) -> dict[int, int]:
        return self._connector.member_counts(collection_ids)

    def item_ids_by_external_id(self, library_id: int, external_ids: List[str]) -> dict[str, int]:
        return self._connector.item_ids_by_external_id(library_id, external_ids)

    def collections_for_item(self, item_id: int) -> List[LibraryCollection]:
        return self._connector.collections_for_item(item_id)
