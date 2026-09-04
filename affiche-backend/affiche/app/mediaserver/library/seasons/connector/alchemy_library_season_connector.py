from typing import Mapping, Optional, List

from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.connector.batch_upsert import commit_batch_with_fallback
from affiche.app.mediaserver.library.model import LibrarySeason, SeasonPosterState
from affiche.app.mediaserver.library.seasons.connector.library_season_entity import LibrarySeasonEntity

class AlchemyLibrarySeasonConnector:

    def __init__(self, session: Session):
        self._session = session

    def update_seasons(self, seasons: List[LibrarySeason], state: SeasonPosterState) -> None:
        changes = state.changes()
        if not seasons or not changes:
            return
        stmt = (update(LibrarySeasonEntity)
                .where(LibrarySeasonEntity.id.in_([season.id for season in seasons]))
                .values(**changes))
        self._session.execute(stmt)
        self._session.commit()

    def rekey_seasons(self, adoptions: Mapping[int, str]) -> int:
        rekeyed = 0
        for season_id, external_id in adoptions.items():
            entity = self._session.get(LibrarySeasonEntity, season_id)
            if entity is None:
                continue
            entity.external_id = external_id
            entity.poster_hash = None
            rekeyed += 1
        self._session.commit()
        return rekeyed

    def create_or_update_seasons_batch(self, seasons: List[LibrarySeason]) -> None:
        commit_batch_with_fallback(
            self._session,
            seasons,
            build_stmt=self._season_upsert_stmt,
            describe=lambda s: f"external_id={s.external_id} show_id={s.show_id} library_id={s.library_id}",
        )

    def _season_upsert_stmt(self, season: LibrarySeason):
        data = season.model_dump(exclude={'id', 'processed'})
        stmt = insert(LibrarySeasonEntity).values(**data, processed=False)
        return stmt.on_conflict_do_update(
            index_elements=['external_id', 'show_id', 'library_id'],
            set_={col: stmt.excluded[col] for col in self._season_update_columns()}
        )

    def get_seasons_by_show(self,
                            show_id: int,
                            library_id: int,
                            processed: Optional[bool] = None) -> List[LibrarySeason]:
        query = (self._session.query(LibrarySeasonEntity)
                 .filter(LibrarySeasonEntity.show_id == show_id)
                 .filter(LibrarySeasonEntity.library_id == library_id))

        if processed is not None:
            query = query.filter(LibrarySeasonEntity.processed == processed)

        return [LibrarySeason.model_validate(s) for s in query.all()]

    def _season_update_columns(self) -> list[str]:
        return [
            'season_number',
            'title',
            'added_at',
            'updated_at',
            'imdb_id',
            'tmdb_id',
            'tvdb_id',
            'poster_url',
        ]
