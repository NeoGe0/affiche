from typing import List, Sequence

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.episodes.library_episode_repository import LibraryEpisodeRepository
from affiche.app.mediaserver.library.episodes.model.library_episode import LibraryEpisode

class LibraryEpisodeService:

    def __init__(self, session: Session):
        self._repository = LibraryEpisodeRepository(session)

    def create_or_update(self, episodes: List[LibraryEpisode]) -> None:
        self._repository.create_or_update(episodes)

    def delete_episodes_of_seasons(self, season_ids: Sequence[int]) -> int:
        return self._repository.delete_episodes_of_seasons(season_ids)

    def get_season_episodes(self, season_id: int) -> List[LibraryEpisode]:
        return self._repository.get_episodes_by_season(season_id)
