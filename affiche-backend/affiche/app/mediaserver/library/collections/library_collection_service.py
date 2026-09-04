import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.collections.library_collection_repository import (
    LibraryCollectionRepository,
)
from affiche.app.mediaserver.library.collections.model.library_collection import (
    LibraryCollection,
    LibraryCollectionSearch,
)
from affiche.app.mediaserver.library.model import LibraryItem, LibraryItemSearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.service.media_server_connector_protocol import CollectionWriter

logger = logging.getLogger(__name__)

class CollectionWriteError(Exception):

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class LibraryCollectionService:

    def __init__(self, session: Session, connector_factory: Optional[object] = None):
        self._session = session
        self._repository = LibraryCollectionRepository(session)
        self._library_repository = LibraryRepository(session)
        self._connector_factory = connector_factory

    def _writer(self, media_server_id: int) -> CollectionWriter:
        if self._connector_factory is None:
            raise CollectionWriteError("No media server connection is configured.")
        return self._connector_factory.get(media_server_id)

    def find_collections(self, search: LibraryCollectionSearch) -> List[LibraryCollection]:
        return self._repository.find_collections(search)

    def count_collections(self, search: LibraryCollectionSearch) -> int:
        return self._repository.count_collections(search)

    def get_collection(self, media_server_id: int, library_id: int,
                       collection_id: int) -> LibraryCollection:
        self._library_repository.get_library(media_server_id, library_id)
        return self._repository.get_collection(library_id, collection_id)

    def member_counts(self, collections: List[LibraryCollection]) -> dict[int, int]:
        return self._repository.member_counts([c.id for c in collections])

    def get_members(self, media_server_id: int, library_id: int,
                    collection_id: int) -> List[LibraryItem]:
        self.get_collection(media_server_id, library_id, collection_id)
        item_ids = self._repository.member_ids(collection_id)
        if not item_ids:
            return []
        return self._library_repository.find_items(
            LibraryItemSearch(library_id=library_id, item_ids=item_ids))

    def collections_for_item(self, item_id: int) -> List[LibraryCollection]:
        return self._repository.collections_for_item(item_id)

    def set_locked(self, media_server_id: int, library_id: int, collection_id: int,
                   locked: bool) -> LibraryCollection:
        collection = self.get_collection(media_server_id, library_id, collection_id)
        collection.locked = locked
        return self._repository.create_or_update(collection)

    def sync_collections(self,
                         library_id: int,
                         fetched: List[dict],
                         seen_at: Optional[datetime] = None,
                         drop_empty: bool = False) -> None:
        seen_at = seen_at or datetime.now(timezone.utc)

        if drop_empty:
            fetched = [entry for entry in fetched
                       if self._mapped_member_ids(library_id, entry)]

        self._repository.create_or_update_batch([
            LibraryCollection(
                library_id=library_id,
                external_id=entry['external_id'],
                title=entry['title'],
                sort_title=entry.get('sort_title'),
                child_count=entry.get('child_count'),
                added_at=entry.get('added_at'),
                updated_at=entry.get('updated_at'),
                last_seen_at=seen_at,
                poster_url=entry.get('poster_url'),
            )
            for entry in fetched
        ])
        self._session.commit()

        for entry in fetched:
            stored = self._repository.find_by_external_id(library_id, entry['external_id'])
            if stored is None:
                continue
            self._store_members(library_id, stored.id, entry)

        soft_deleted = self._repository.reconcile_deletions(library_id, seen_at)
        self._session.commit()
        logger.info("[sync] library %d: %d collection(s), %d no longer on the server",
                    library_id, len(fetched), soft_deleted)

    def _mapped_member_ids(self, library_id: int, entry: dict) -> List[int]:
        external_ids = entry.get('member_external_ids') or []
        by_external = self._repository.item_ids_by_external_id(library_id, external_ids)
        return [by_external[external] for external in external_ids if external in by_external]

    def _store_members(self, library_id: int, collection_id: int, entry: dict) -> None:
        self._repository.set_members(collection_id, self._mapped_member_ids(library_id, entry))

    def create_collection(self,
                          media_server_id: int,
                          library_id: int,
                          title: str,
                          item_ids: List[int]) -> LibraryCollection:
        connector = self._writer(media_server_id)
        library = self._library_repository.get_library(media_server_id, library_id)
        items = self._items(library_id, item_ids)
        if not items:
            raise CollectionWriteError("A collection needs at least one item that Affiche knows about.")

        external_id = connector.create_collection(library.external_id, title,
                                                  [item.external_id for item in items])
        if not external_id:
            raise CollectionWriteError(f"The media server would not create the collection '{title}'.")

        self._repository.create_or_update_batch([LibraryCollection(
            library_id=library_id,
            external_id=str(external_id),
            title=title,
            child_count=len(items),
            added_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )])
        self._session.commit()

        stored = self._repository.find_by_external_id(library_id, str(external_id))
        self._repository.set_members(stored.id, [item.id for item in items])
        return stored

    def rename_collection(self, media_server_id: int, library_id: int, collection_id: int,
                          title: str) -> LibraryCollection:
        connector = self._writer(media_server_id)
        collection = self.get_collection(media_server_id, library_id, collection_id)
        if not connector.rename_collection(collection.external_id, title):
            raise CollectionWriteError("The media server would not rename the collection.")

        collection.title = title
        return self._repository.create_or_update(collection)

    def delete_collection(self, media_server_id: int, library_id: int,
                          collection_id: int) -> None:
        connector = self._writer(media_server_id)
        collection = self.get_collection(media_server_id, library_id, collection_id)
        if not connector.delete_collection(collection.external_id):
            raise CollectionWriteError("The media server would not delete the collection.")

        self._repository.delete_collection(library_id, collection_id)

    def add_items(self, media_server_id: int, library_id: int, collection_id: int,
                  item_ids: List[int]) -> int:
        connector = self._writer(media_server_id)
        collection = self.get_collection(media_server_id, library_id, collection_id)
        items = self._items(library_id, item_ids)
        if not items:
            return 0

        if not connector.add_to_collection(collection.external_id,
                                           [item.external_id for item in items]):
            raise CollectionWriteError("The media server would not add those items.")

        self._repository.add_members(collection_id, [item.id for item in items])
        return len(items)

    def remove_items(self, media_server_id: int, library_id: int, collection_id: int,
                     item_ids: List[int]) -> int:
        connector = self._writer(media_server_id)
        collection = self.get_collection(media_server_id, library_id, collection_id)
        items = self._items(library_id, item_ids)
        if not items:
            return 0

        if not connector.remove_from_collection(collection.external_id,
                                                [item.external_id for item in items]):
            raise CollectionWriteError("The media server would not remove those items.")

        self._repository.remove_members(collection_id, [item.id for item in items])
        return len(items)

    def _items(self, library_id: int, item_ids: List[int]) -> List[LibraryItem]:
        if not item_ids:
            return []
        return self._library_repository.find_items(
            LibraryItemSearch(library_id=library_id, item_ids=item_ids))
