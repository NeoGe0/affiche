from typing import List, Sequence

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.connector.batch_upsert import commit_batch_with_fallback
from affiche.app.mediaserver.library.episodes.connector.library_episode_entity import LibraryEpisodeEntity
from affiche.app.mediaserver.library.model import LibraryEpisode
from affiche.external.media_quality import MEDIA_FIELDS

class AlchemyLibraryEpisodeConnector:

    def __init__(self, session: Session):
        self._session = session

    def create_or_update_episodes_batch(self, episodes: List[LibraryEpisode]) -> None:
        commit_batch_with_fallback(
            self._session,
            episodes,
            build_stmt=self._episode_upsert_stmt,
            describe=lambda e: f"external_id={e.external_id} season_id={e.season_id} library_id={e.library_id}",
        )

    def _episode_upsert_stmt(self, episode: LibraryEpisode):
        data = episode.model_dump(exclude={'id'})
        stmt = insert(LibraryEpisodeEntity).values(**data)
        return stmt.on_conflict_do_update(
            index_elements=['external_id', 'season_id', 'library_id'],
            set_={col: stmt.excluded[col] for col in self._episode_update_columns()}
        )

    def delete_episodes_of_seasons(self, season_ids: Sequence[int]) -> int:
        if not season_ids:
            return 0
        deleted = (self._session.query(LibraryEpisodeEntity)
                   .filter(LibraryEpisodeEntity.season_id.in_(season_ids))
                   .delete(synchronize_session=False))
        self._session.commit()
        return deleted

    def get_episodes_by_season(self, season_id: int) -> List[LibraryEpisode]:
        query = (self._session.query(LibraryEpisodeEntity)
                 .filter(LibraryEpisodeEntity.season_id == season_id)
                 .order_by(LibraryEpisodeEntity.episode_number))
        return [LibraryEpisode.model_validate(e) for e in query.all()]

    def _episode_update_columns(self) -> list[str]:
        return [
            'season_number',
            'episode_number',
            'title',
            'air_date',
            'added_at',
            'updated_at',
            'imdb_id',
            'tmdb_id',
            'tvdb_id',
            *MEDIA_FIELDS,
        ]
