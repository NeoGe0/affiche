from typing import List, Mapping, Optional, Set

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.seasons.library_season_repository import LibrarySeasonRepository
from affiche.app.mediaserver.library.seasons.model.library_season import (
    LibrarySeason,
    SeasonPosterState,
)
from affiche.app.mediaserver.library.sync.reidentification import match_readded_seasons

class LibrarySeasonService:

    def __init__(self, session: Session):
        self._repository = LibrarySeasonRepository(session)

    def update_seasons(self, seasons: List[LibrarySeason], state: SeasonPosterState) -> None:
        self._repository.update_seasons(seasons, state)

    def adopt_readded_seasons(self,
                              library_id: int,
                              show_id: int,
                              incoming: Mapping[int, str]) -> List[int]:
        existing = self._repository.get_seasons_by_show(show_id=show_id, library_id=library_id)
        adoptions = match_readded_seasons(existing, incoming)
        if not adoptions:
            return []
        self._repository.rekey_seasons(adoptions)
        return list(adoptions)

    def create_or_update(self, seasons: List[LibrarySeason]) -> None:
        self._repository.create_or_update(seasons)

    def get_season(self,
                   library_id: int,
                   item_id: int,
                   season_number: int) -> Optional[LibrarySeason]:
        seasons = self._repository.get_seasons_by_show(show_id=item_id, library_id=library_id)
        return next((s for s in seasons if s.season_number == season_number), None)

    def set_tmdb_match(self,
                       season_id: int,
                       tmdb_id: Optional[int],
                       season_number: Optional[int]) -> Optional[LibrarySeason]:
        return self._repository.set_tmdb_match(season_id, tmdb_id, season_number)

    def get_item_seasons(self,
                         library_id: int,
                         item_id: int,
                         processed: Optional[bool] = None) -> List[LibrarySeason]:
        return self._repository.get_seasons_by_show(show_id=item_id, library_id=library_id, processed=processed)

    def find_known_external_ids(self, library_id: int, external_ids: List[str]) -> Set[str]:
        return self._repository.find_known_external_ids(library_id, external_ids)

    def find_show_ids(self,
                      library_id: int,
                      processed: bool,
                      uploaded: Optional[bool] = None) -> List[int]:
        return self._repository.find_show_ids(library_id, processed, uploaded)
