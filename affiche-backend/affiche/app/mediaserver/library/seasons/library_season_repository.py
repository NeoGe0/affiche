from typing import List, Mapping, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.library.seasons.connector.alchemy_library_season_connector import AlchemyLibrarySeasonConnector
from affiche.app.mediaserver.library.seasons.model.library_season import (
    LibrarySeason,
    SeasonPosterState,
)

class LibrarySeasonRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyLibrarySeasonConnector(session)

    def update_seasons(self, seasons: List[LibrarySeason], state: SeasonPosterState) -> None:
        self._connector.update_seasons(seasons, state)

    def rekey_seasons(self, adoptions: Mapping[int, str]) -> int:
        return self._connector.rekey_seasons(adoptions)

    def create_or_update(self, seasons: List[LibrarySeason]) -> None:
        self._connector.create_or_update_seasons_batch(seasons)

    def get_seasons_by_show(self,
                            show_id: int,
                            library_id: int,
                            processed: Optional[bool] = None) -> List[LibrarySeason]:
        return self._connector.get_seasons_by_show(show_id, library_id, processed)

