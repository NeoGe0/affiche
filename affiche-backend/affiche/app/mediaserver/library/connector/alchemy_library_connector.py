from datetime import datetime
from typing import Mapping, Optional, List

from sqlalchemy import and_, case, distinct, exists, func, not_, or_, select, union
from sqlalchemy.dialects.sqlite import insert

from sqlalchemy.orm import Session, Query
from affiche.app.mediaserver.library.connector.batch_upsert import commit_batch_with_fallback
from affiche.app.mediaserver.library.connector.library_entity import LibraryEntity

from affiche.app.mediaserver.library.collections.connector.library_collection_entity import (
    LibraryCollectionEntity,
)
from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity
from affiche.app.mediaserver.library.seasons.connector.library_season_entity import (
    LibrarySeasonEntity,
)
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.model.library_item_search import (
    NO_PROVIDER, LibraryItemSearch,
)
from affiche.app.mediaserver.library.model.search_criteria import SortDir
from affiche.app.mediaserver.library.model.library_item_stats import LibraryItemStats

def bucket_letter(title: Optional[str]) -> str:
    ch = (title or "").strip()[:1].upper()
    return ch if "A" <= ch <= "Z" else "#"

SORTABLE_COLUMNS = {
    'title': LibraryItemEntity.title,
    'year': LibraryItemEntity.year,
    'release_date': LibraryItemEntity.release_date,
    'added_at': LibraryItemEntity.added_at,
    'resolution': LibraryItemEntity.media_height,
    'codec': LibraryItemEntity.video_codec,
    'size': LibraryItemEntity.media_size_bytes,
    'status': LibraryItemEntity.processed,
    'provider': LibraryItemEntity.poster_provider,
    'deleted_at': LibraryItemEntity.deleted_at,
}

def _pending_clause():
    return and_(LibraryItemEntity.processed.is_(False), LibraryItemEntity.error_message.is_(None))

def _error_clause():
    return LibraryItemEntity.error_message.is_not(None)

def _attempted_clause():
    return or_(LibraryItemEntity.processed.is_(True), _error_clause())

def _season_provider_exists(clause):
    return exists().where(and_(LibrarySeasonEntity.show_id == LibraryItemEntity.id, clause))

def _provider_clause(provider: str):
    if provider == NO_PROVIDER:
        return and_(LibraryItemEntity.poster_provider.is_(None),
                    not_(_season_provider_exists(LibrarySeasonEntity.poster_provider.is_not(None))))
    return or_(LibraryItemEntity.poster_provider == provider,
               _season_provider_exists(LibrarySeasonEntity.poster_provider == provider))

def _bucket_sums():
    return {
        'total': func.count(),
        'processed': func.sum(case((LibraryItemEntity.processed.is_(True), 1), else_=0)),
        'unprocessed': func.sum(case((_pending_clause(), 1), else_=0)),
        'errors': func.sum(case((_error_clause(), 1), else_=0)),
        'locked': func.sum(case((LibraryItemEntity.locked.is_(True), 1), else_=0)),
        'uploaded': func.sum(case((LibraryItemEntity.poster_uploaded_at.is_not(None), 1), else_=0)),
    }

def _stats_from_row(row) -> LibraryItemStats:
    return LibraryItemStats(**{field: value or 0
                               for field, value in zip(_bucket_sums(), row)})

class AlchemyLibraryConnector:

    def __init__(self, session: Session):
        self._session = session

    def find_library(self,
                     media_server_id: int,
                     library_id: int) -> Optional[Library]:
        entity = (self._session.query(LibraryEntity)
                  .where(LibraryEntity.media_server_id == media_server_id)
                  .where(LibraryEntity.id == library_id)
                  .first())
        return Library.model_validate(entity) if entity else None

    def update_item(self, item: LibraryItem) -> LibraryItem:
        entity = self._session.get(LibraryItemEntity, item.id)
        for field, value in item.model_dump(exclude_unset=True).items():
            setattr(entity, field, value)
        self._session.commit()
        self._session.refresh(entity)
        return LibraryItem.model_validate(entity)

    def create_library(self, library: Library) -> Library:
        entity = LibraryEntity(**library.model_dump(exclude_none=True))
        self._session.add(entity)
        self._session.flush()

        return Library.model_validate(entity)

    def set_library_enabled(self,
                            media_server_id: int,
                            library_id: int,
                            enabled: bool) -> Optional[Library]:
        entity = (self._session.query(LibraryEntity)
                  .where(LibraryEntity.media_server_id == media_server_id)
                  .where(LibraryEntity.id == library_id)
                  .first())
        if entity is None:
            return None
        entity.enabled = enabled
        self._session.commit()
        self._session.refresh(entity)
        return Library.model_validate(entity)

    def find_libraries(self, search: LibrarySearch) -> List[Library]:
        query = (self._session.query(LibraryEntity)
                 .where(LibraryEntity.media_server_id == search.media_server_id))
        if search.enabled is not None:
            query = query.filter(LibraryEntity.enabled == search.enabled)

        return [Library.model_validate(lib) for lib in query.all()]

    def delete_library(self, media_server_id: int, library_id: int) -> bool:
        entity = (self._session.query(LibraryEntity)
                  .where(LibraryEntity.media_server_id == media_server_id)
                  .where(LibraryEntity.id == library_id)
                  .first())
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True

    def create_or_update_items_batch(self, items: List[LibraryItem]) -> None:
        commit_batch_with_fallback(
            self._session,
            items,
            build_stmt=self._item_upsert_stmt,
            describe=lambda item: f"external_id={item.external_id} library_id={item.library_id}",
        )

    def _item_upsert_stmt(self, item: LibraryItem):
        data = item.model_dump(exclude={'id', 'processed'})
        stmt = insert(LibraryItemEntity).values(**data, processed=False)
        return stmt.on_conflict_do_update(
            index_elements=['external_id', 'library_id'],
            set_={col: stmt.excluded[col] for col in self._update_columns()}
        )

    def _search_query(self, search: LibraryItemSearch) -> Query:
        query = self._session.query(LibraryItemEntity)

        if search.library_ids is not None:
            query = query.filter(LibraryItemEntity.library_id.in_(search.library_ids))
        elif search.library_id is not None:
            query = query.filter(LibraryItemEntity.library_id == search.library_id)

        if search.deleted is False:
            query = query.filter(LibraryItemEntity.deleted_at.is_(None))
        elif search.deleted is True:
            query = query.filter(LibraryItemEntity.deleted_at.is_not(None))

        if search.deleted_before is not None:
            query = query.filter(LibraryItemEntity.deleted_at < search.deleted_before)

        if search.processed is not None:
            query = query.filter(LibraryItemEntity.processed == search.processed)

        if search.has_error is not None:
            query = query.filter(_error_clause() if search.has_error
                                 else LibraryItemEntity.error_message.is_(None))

        if search.provider is not None:
            query = query.filter(_provider_clause(search.provider))

        if search.locked is not None:
            query = query.filter(LibraryItemEntity.locked == search.locked)

        if search.attempted is not None:
            query = query.filter(_attempted_clause() if search.attempted
                                 else not_(_attempted_clause()))

        if search.uploaded is not None:
            query = query.filter(LibraryItemEntity.poster_uploaded_at.is_not(None) if search.uploaded
                                 else LibraryItemEntity.poster_uploaded_at.is_(None))

        if search.external_ids is not None:
            query = query.filter(LibraryItemEntity.external_id.in_(search.external_ids))

        if search.item_ids is not None:
            query = query.filter(LibraryItemEntity.id.in_(search.item_ids))

        if search.search:
            query = query.filter(LibraryItemEntity.title.ilike(f"%{search.search}%"))

        return query

    def _ordered(self, query: Query, search: LibraryItemSearch) -> Query:
        column = SORTABLE_COLUMNS.get(search.sort_by, LibraryItemEntity.title)
        order = column.desc() if search.sort_dir is SortDir.DESC else column.asc()
        if column is LibraryItemEntity.title:
            return query.order_by(order)
        return query.order_by(order, LibraryItemEntity.title.asc())

    def _paged(self, query: Query, search: LibraryItemSearch) -> Query:
        if search.page_size is None:
            return query
        return query.offset(search.offset).limit(search.limit)

    def find_items(self, search: LibraryItemSearch) -> List[LibraryItem]:
        query = self._paged(self._ordered(self._search_query(search), search), search)
        return [LibraryItem.model_validate(item) for item in query.all()]

    def count_items(self, search: LibraryItemSearch) -> int:
        return self._search_query(search).count()

    def count_items_per_library(self, search: LibraryItemSearch) -> dict[int, int]:
        if search.library_ids is not None and not search.library_ids:
            return {}
        rows = (self._search_query(search)
                .with_entities(LibraryItemEntity.library_id, func.count())
                .group_by(LibraryItemEntity.library_id)
                .all())
        return {library_id: count for library_id, count in rows}

    def count_status_buckets(self, search: LibraryItemSearch) -> LibraryItemStats:
        row = self._search_query(search).with_entities(*_bucket_sums().values()).one()
        return _stats_from_row(row)

    def count_buckets_per_library(self, search: LibraryItemSearch) -> dict[int, LibraryItemStats]:
        if search.library_ids is not None and not search.library_ids:
            return {}
        rows = (self._search_query(search)
                .with_entities(LibraryItemEntity.library_id, *_bucket_sums().values())
                .group_by(LibraryItemEntity.library_id)
                .all())
        return {row[0]: _stats_from_row(row[1:]) for row in rows}

    def count_items_by_provider(self, search: LibraryItemSearch) -> dict[Optional[str], int]:
        base = self._search_query(search).subquery()
        own = (select(base.c.id.label('item_id'), base.c.poster_provider.label('provider'))
               .where(base.c.poster_provider.is_not(None)))
        through_a_season = (
            select(LibrarySeasonEntity.show_id.label('item_id'),
                   LibrarySeasonEntity.poster_provider.label('provider'))
            .join(base, base.c.id == LibrarySeasonEntity.show_id)
            .where(LibrarySeasonEntity.poster_provider.is_not(None)))
        matched = union(own, through_a_season).subquery()

        counts: dict[Optional[str], int] = {
            provider: count for provider, count in
            (self._session.query(matched.c.provider, func.count(distinct(matched.c.item_id)))
             .group_by(matched.c.provider).all())
        }

        unrecorded = self._search_query(search).filter(_provider_clause(NO_PROVIDER)).count()
        if unrecorded:
            counts[None] = unrecorded
        return counts

    def count_posters_by_provider(self, search: LibraryItemSearch) -> dict[Optional[str], int]:
        item_rows = (self._search_query(search)
                     .with_entities(LibraryItemEntity.poster_provider, func.count())
                     .group_by(LibraryItemEntity.poster_provider)
                     .all())

        base = self._search_query(search).subquery()
        season_rows = (self._session.query(LibrarySeasonEntity.poster_provider, func.count())
                       .join(base, base.c.id == LibrarySeasonEntity.show_id)
                       .group_by(LibrarySeasonEntity.poster_provider)
                       .all())

        collection_rows = (self._collection_scope(search)
                           .with_entities(LibraryCollectionEntity.poster_provider, func.count())
                           .group_by(LibraryCollectionEntity.poster_provider)
                           .all())

        counts: dict[Optional[str], int] = {}
        for provider, count in [*item_rows, *season_rows, *collection_rows]:
            counts[provider] = counts.get(provider, 0) + count
        return counts

    def _collection_scope(self, search: LibraryItemSearch) -> Query:
        query = (self._session.query(LibraryCollectionEntity)
                 .filter(LibraryCollectionEntity.deleted_at.is_(None)))
        if search.library_ids is not None:
            return query.filter(LibraryCollectionEntity.library_id.in_(search.library_ids))
        if search.library_id is not None:
            return query.filter(LibraryCollectionEntity.library_id == search.library_id)
        return query

    def count_style_staleness(self, search: LibraryItemSearch, current_hash: str) -> tuple[int, int]:
        row = (self._search_query(search)
               .with_entities(
                   func.count(),
                   func.sum(case((and_(LibraryItemEntity.style_hash.is_not(None),
                                       LibraryItemEntity.style_hash != current_hash), 1), else_=0)))
               .one())
        return int(row[1] or 0), int(row[0] or 0)

    def letter_offsets(self, search: LibraryItemSearch) -> List[tuple[str, int]]:
        query = self._ordered(self._search_query(search), search).with_entities(LibraryItemEntity.title)

        offsets: List[tuple[str, int]] = []
        seen: set[str] = set()
        for index, (title,) in enumerate(query.all()):
            letter = bucket_letter(title)
            if letter not in seen:
                seen.add(letter)
                offsets.append((letter, index))
        return offsets

    def get_library_item(self, library_id: int, item_id: int) -> Optional[LibraryItem]:
        entity = (
            self._session.query(LibraryItemEntity)
            .filter_by(id=item_id, library_id=library_id)
            .first()
        )
        return LibraryItem.model_validate(entity) if entity else None

    def reconcile_deletions(self, library_id: int, seen_at: datetime) -> tuple[int, int]:
        soft_deleted = (
            self._session.query(LibraryItemEntity)
            .filter(LibraryItemEntity.library_id == library_id)
            .filter(LibraryItemEntity.deleted_at.is_(None))
            .filter(or_(LibraryItemEntity.last_seen_at < seen_at,
                        LibraryItemEntity.last_seen_at.is_(None)))
            .update({LibraryItemEntity.deleted_at: seen_at}, synchronize_session=False)
        )
        restored = (
            self._session.query(LibraryItemEntity)
            .filter(LibraryItemEntity.library_id == library_id)
            .filter(LibraryItemEntity.deleted_at.is_not(None))
            .filter(LibraryItemEntity.last_seen_at == seen_at)
            .update({LibraryItemEntity.deleted_at: None}, synchronize_session=False)
        )
        return soft_deleted, restored

    def rekey_items(self, adoptions: Mapping[int, str]) -> int:
        rekeyed = 0
        for item_id, external_id in adoptions.items():
            entity = self._session.get(LibraryItemEntity, item_id)
            if entity is None:
                continue
            entity.external_id = external_id
            entity.poster_hash = None
            entity.poster_uploaded_at = None
            rekeyed += 1
        self._session.commit()
        return rekeyed

    def restore_item(self, library_id: int, item_id: int) -> Optional[LibraryItem]:
        entity = (
            self._session.query(LibraryItemEntity)
            .filter_by(id=item_id, library_id=library_id)
            .filter(LibraryItemEntity.deleted_at.is_not(None))
            .first()
        )
        if entity is None:
            return None
        entity.deleted_at = None
        self._session.commit()
        self._session.refresh(entity)
        return LibraryItem.model_validate(entity)

    def hard_delete_items(self, item_ids: List[int]) -> int:
        if not item_ids:
            return 0
        deleted = (self._session.query(LibraryItemEntity)
                   .filter(LibraryItemEntity.id.in_(item_ids))
                   .delete(synchronize_session=False))
        self._session.commit()
        return deleted

    def _update_columns(self) -> list[str]:
        return [
            'title',
            'type',
            'year',
            'release_date',
            'added_at',
            'updated_at',
            'last_seen_at',
            'imdb_id',
            'tmdb_id',
            'tvdb_id',
            'poster_url',
            'media_resolution',
            'media_width',
            'media_height',
            'video_codec',
            'audio_codec',
            'audio_channels',
            'media_container',
            'media_bitrate',
            'media_size_bytes',
        ]
