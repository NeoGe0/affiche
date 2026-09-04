from datetime import datetime
from typing import List, Optional

from sqlalchemy import delete, func, or_, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Query, Session

from affiche.app.mediaserver.library.collections.connector.library_collection_entity import (
    LibraryCollectionEntity,
)
from affiche.app.mediaserver.library.collections.connector.library_collection_member_entity import (
    LibraryCollectionMemberEntity,
)
from affiche.app.mediaserver.library.collections.model.library_collection import (
    CollectionPosterState,
    LibraryCollection,
    LibraryCollectionSearch,
)
from affiche.app.mediaserver.library.connector.batch_upsert import commit_batch_with_fallback
from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity
from affiche.app.mediaserver.library.model.search_criteria import SortDir

SORTABLE_COLUMNS = {
    'title': LibraryCollectionEntity.title,
    'added_at': LibraryCollectionEntity.added_at,
    'size': LibraryCollectionEntity.child_count,
    'status': LibraryCollectionEntity.processed,
}

class AlchemyLibraryCollectionConnector:

    def __init__(self, session: Session):
        self._session = session

    def _search_query(self, search: LibraryCollectionSearch) -> Query:
        query = self._session.query(LibraryCollectionEntity)

        if search.library_ids is not None:
            query = query.filter(LibraryCollectionEntity.library_id.in_(search.library_ids))
        elif search.library_id is not None:
            query = query.filter(LibraryCollectionEntity.library_id == search.library_id)

        if search.collection_ids is not None:
            query = query.filter(LibraryCollectionEntity.id.in_(search.collection_ids))

        if search.deleted is False:
            query = query.filter(LibraryCollectionEntity.deleted_at.is_(None))
        elif search.deleted is True:
            query = query.filter(LibraryCollectionEntity.deleted_at.is_not(None))

        if search.processed is not None:
            query = query.filter(LibraryCollectionEntity.processed == search.processed)

        if search.locked is not None:
            query = query.filter(LibraryCollectionEntity.locked == search.locked)

        if search.search:
            query = query.filter(LibraryCollectionEntity.title.ilike(f"%{search.search}%"))

        return query

    def find_collections(self, search: LibraryCollectionSearch) -> List[LibraryCollection]:
        column = SORTABLE_COLUMNS.get(search.sort_by, LibraryCollectionEntity.title)
        order = column.desc() if search.sort_dir is SortDir.DESC else column.asc()
        query = self._search_query(search).order_by(order, LibraryCollectionEntity.title.asc())
        if search.page_size is not None:
            query = query.offset(search.offset).limit(search.page_size)
        return [LibraryCollection.model_validate(row) for row in query.all()]

    def count_collections(self, search: LibraryCollectionSearch) -> int:
        return self._search_query(search).count()

    def get_collection(self, library_id: int, collection_id: int) -> Optional[LibraryCollection]:
        entity = (self._session.query(LibraryCollectionEntity)
                  .filter_by(id=collection_id, library_id=library_id)
                  .first())
        return LibraryCollection.model_validate(entity) if entity else None

    def find_by_external_id(self, library_id: int, external_id: str) -> Optional[LibraryCollection]:
        entity = (self._session.query(LibraryCollectionEntity)
                  .filter_by(library_id=library_id, external_id=external_id)
                  .first())
        return LibraryCollection.model_validate(entity) if entity else None

    def update_collection(self, collection: LibraryCollection) -> LibraryCollection:
        entity = self._session.get(LibraryCollectionEntity, collection.id)
        for field, value in collection.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        self._session.commit()
        self._session.refresh(entity)
        return LibraryCollection.model_validate(entity)

    def create_or_update_batch(self, collections: List[LibraryCollection]) -> None:
        commit_batch_with_fallback(
            self._session,
            collections,
            build_stmt=self._upsert_stmt,
            describe=lambda c: f"external_id={c.external_id} library_id={c.library_id}",
        )

    def _upsert_stmt(self, collection: LibraryCollection):
        data = collection.model_dump(exclude={'id', 'processed', 'locked'})
        stmt = insert(LibraryCollectionEntity).values(**data, processed=False)
        return stmt.on_conflict_do_update(
            index_elements=['external_id', 'library_id'],
            set_={col: stmt.excluded[col] for col in self._update_columns()}
        )

    def _update_columns(self) -> list[str]:
        return ['title', 'sort_title', 'child_count', 'added_at', 'updated_at', 'last_seen_at',
                'poster_url']

    def delete_collection(self, library_id: int, collection_id: int) -> bool:
        entity = (self._session.query(LibraryCollectionEntity)
                  .filter_by(id=collection_id, library_id=library_id)
                  .first())
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True

    def reconcile_deletions(self, library_id: int, seen_at: datetime) -> int:
        return (self._session.query(LibraryCollectionEntity)
                .filter(LibraryCollectionEntity.library_id == library_id)
                .filter(LibraryCollectionEntity.deleted_at.is_(None))
                .filter(or_(LibraryCollectionEntity.last_seen_at < seen_at,
                            LibraryCollectionEntity.last_seen_at.is_(None)))
                .update({LibraryCollectionEntity.deleted_at: seen_at}, synchronize_session=False))

    def restore_seen(self, library_id: int, seen_at: datetime) -> int:
        return (self._session.query(LibraryCollectionEntity)
                .filter(LibraryCollectionEntity.library_id == library_id)
                .filter(LibraryCollectionEntity.deleted_at.is_not(None))
                .filter(LibraryCollectionEntity.last_seen_at == seen_at)
                .update({LibraryCollectionEntity.deleted_at: None}, synchronize_session=False))

    def set_members(self, collection_id: int, item_ids: List[int]) -> None:
        self._session.execute(
            delete(LibraryCollectionMemberEntity)
            .where(LibraryCollectionMemberEntity.collection_id == collection_id)
        )
        if item_ids:
            self._session.execute(
                insert(LibraryCollectionMemberEntity).values(
                    [{"collection_id": collection_id, "item_id": item_id}
                     for item_id in dict.fromkeys(item_ids)]
                ).on_conflict_do_nothing()
            )
        self._session.commit()

    def add_members(self, collection_id: int, item_ids: List[int]) -> None:
        if not item_ids:
            return
        self._session.execute(
            insert(LibraryCollectionMemberEntity).values(
                [{"collection_id": collection_id, "item_id": item_id}
                 for item_id in dict.fromkeys(item_ids)]
            ).on_conflict_do_nothing()
        )
        self._session.commit()

    def remove_members(self, collection_id: int, item_ids: List[int]) -> None:
        if not item_ids:
            return
        self._session.execute(
            delete(LibraryCollectionMemberEntity)
            .where(LibraryCollectionMemberEntity.collection_id == collection_id)
            .where(LibraryCollectionMemberEntity.item_id.in_(item_ids))
        )
        self._session.commit()

    def member_ids(self, collection_id: int) -> List[int]:
        rows = (self._session.query(LibraryCollectionMemberEntity.item_id)
                .filter(LibraryCollectionMemberEntity.collection_id == collection_id)
                .all())
        return [item_id for (item_id,) in rows]

    def member_counts(self, collection_ids: List[int]) -> dict[int, int]:
        if not collection_ids:
            return {}
        rows = (self._session.query(LibraryCollectionMemberEntity.collection_id, func.count())
                .filter(LibraryCollectionMemberEntity.collection_id.in_(collection_ids))
                .group_by(LibraryCollectionMemberEntity.collection_id)
                .all())
        return {collection_id: count for collection_id, count in rows}

    def item_ids_by_external_id(self, library_id: int, external_ids: List[str]) -> dict[str, int]:
        if not external_ids:
            return {}
        rows = (self._session.query(LibraryItemEntity.external_id, LibraryItemEntity.id)
                .filter(LibraryItemEntity.library_id == library_id)
                .filter(LibraryItemEntity.external_id.in_(external_ids))
                .all())
        return {external_id: item_id for external_id, item_id in rows}

    def collections_for_item(self, item_id: int) -> List[LibraryCollection]:
        return [LibraryCollection.model_validate(row) for row in
                (self._session.query(LibraryCollectionEntity)
                 .join(LibraryCollectionMemberEntity,
                       LibraryCollectionMemberEntity.collection_id == LibraryCollectionEntity.id)
                 .filter(LibraryCollectionMemberEntity.item_id == item_id)
                 .order_by(LibraryCollectionEntity.title.asc())
                 .all())]

    def update_collections(self, collection_ids: List[int],
                           state: CollectionPosterState) -> None:
        changes = state.changes()
        if not collection_ids or not changes:
            return
        self._session.execute(
            update(LibraryCollectionEntity)
            .where(LibraryCollectionEntity.id.in_(collection_ids))
            .values(**changes)
        )
        self._session.commit()
