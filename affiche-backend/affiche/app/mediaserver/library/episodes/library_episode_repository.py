from typing import List, Sequence

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.episodes.connector.alchemy_library_episode_connector import (
    AlchemyLibraryEpisodeConnector,
)
from affiche.app.mediaserver.library.episodes.model.library_episode import LibraryEpisode

class LibraryEpisodeRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyLibraryEpisodeConnector(session)

    def create_or_update(self, episodes: List[LibraryEpisode]) -> None:
        self._connector.create_or_update_episodes_batch(episodes)

    def delete_episodes_of_seasons(self, season_ids: Sequence[int]) -> int:
        return self._connector.delete_episodes_of_seasons(season_ids)

    def get_episodes_by_season(self, season_id: int) -> List[LibraryEpisode]:
        return self._connector.get_episodes_by_season(season_id)
