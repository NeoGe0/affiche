from typing import Optional

from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.external.poster.poster_service import TmdbSeasonMatch

def tmdb_season_match(season: LibrarySeason) -> Optional[TmdbSeasonMatch]:
    if season.tmdb_id_override is None:
        return None
    number = season.tmdb_season_number_override
    return TmdbSeasonMatch(tmdb_id=season.tmdb_id_override,
                           season_number=season.season_number if number is None else number)
