from typing import List, Optional

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    Library,
    LibraryItem,
    LibraryItemSearch,
    LibrarySearch,
)
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.library.seasons.season_match import tmdb_season_match
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config import Base
from affiche.external.poster.poster_service import PosterAggregatorService, TmdbSeasonMatch
from affiche.external.poster.provider.base_provider import ExternalProvider

class RecordingProvider(ExternalProvider):

    def __init__(self, name: str):
        self._name = name
        self.asked: List[tuple] = []

    @property
    def name(self) -> str:
        return self._name

    def _record(self, season_number, tmdb_id):
        self.asked.append((tmdb_id, season_number))
        return f"{self._name}.jpg"

    def get_season_poster(self, season_number, tmdb_id=None, tvdb_id=None,
                          language=None) -> Optional[str]:
        return self._record(season_number, tmdb_id)

    def get_all_season_posters(self, season_number, tmdb_id=None, tvdb_id=None,
                               language=None) -> List[str]:
        return [self._record(season_number, tmdb_id)]

    def get_movie_poster(self, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_show_poster(self, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_all_posters(self, media_type, tmdb_id=None, tvdb_id=None, language=None):
        return []

    def search_by_title(self, title, media_type, year=None):
        return None

    def get_translated_title(self, media_type, language, tmdb_id=None, tvdb_id=None,
                             season_number=None):
        return None

    def test_connection(self, api_token) -> bool:
        return True

def test_no_override_means_no_match():
    season = LibrarySeason(show_id=1, library_id=1, external_id="s2", season_number=2, title="S2")
    assert tmdb_season_match(season) is None

def test_a_series_without_a_number_keeps_the_seasons_own():
    season = LibrarySeason(show_id=1, library_id=1, external_id="s2", season_number=2, title="S2",
                           tmdb_id_override=225634)
    assert tmdb_season_match(season) == TmdbSeasonMatch(tmdb_id=225634, season_number=2)

def test_the_anthology_case_substitutes_both():
    season = LibrarySeason(show_id=1, library_id=1, external_id="s2", season_number=2, title="S2",
                           tmdb_id_override=225634, tmdb_season_number_override=1)
    assert tmdb_season_match(season) == TmdbSeasonMatch(tmdb_id=225634, season_number=1)

def test_a_number_alone_is_ignored():
    season = LibrarySeason(show_id=1, library_id=1, external_id="s2", season_number=2, title="S2",
                           tmdb_season_number_override=1)
    assert tmdb_season_match(season) is None

@pytest.fixture
def providers():
    tmdb, tvdb = RecordingProvider("tmdb"), RecordingProvider("tvdb")
    return tmdb, tvdb, PosterAggregatorService([tmdb, tvdb])

def test_only_tmdb_is_redirected(providers):
    tmdb, tvdb, aggregator = providers

    aggregator.find_best_season_poster(
        title="Monster", tmdb_id=299939, tvdb_id=389492, season_number=2,
        provider_order=["tmdb", "tvdb"],
        tmdb_match=TmdbSeasonMatch(tmdb_id=225634, season_number=1))

    assert tmdb.asked == [(225634, 1)]
    assert tvdb.asked == []

def test_the_browse_grid_is_redirected_the_same_way(providers):
    tmdb, tvdb, aggregator = providers

    aggregator.get_all_season_posters(
        season_number=2, tmdb_id=299939, tvdb_id=389492,
        tmdb_match=TmdbSeasonMatch(tmdb_id=225634, season_number=1))

    assert tmdb.asked == [(225634, 1)]
    assert tvdb.asked == [(299939, 2)]

def test_without_a_match_nothing_moves(providers):
    tmdb, tvdb, aggregator = providers

    aggregator.get_all_season_posters(season_number=2, tmdb_id=299939, tvdb_id=389492)

    assert tmdb.asked == [(299939, 2)]
    assert tvdb.asked == [(299939, 2)]

@pytest.fixture
def show():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
    db.flush()
    library_service = LibraryService(db)
    library_service.create(Library(media_server_id=server.id, external_id="sec-1", name="Shows",
                                   type="show", language="en", enabled=True))
    db.commit()
    library = library_service.find_libraries(LibrarySearch(media_server_id=server.id))[0]
    library_service.create_or_update_items_batch(
        [LibraryItem(library_id=library.id, external_id="1", title="Monster", type="show",
                     tmdb_id=299939)])
    db.commit()
    item = library_service.find_items(LibraryItemSearch(library_id=library.id))[0]

    seasons = LibrarySeasonService(db)
    seasons.create_or_update([
        LibrarySeason(show_id=item.id, library_id=library.id, external_id=f"s{n}",
                      season_number=n, title=f"Season {n}")
        for n in (1, 2)
    ])
    db.commit()

    yield library_service, seasons, server.id, library.id, item.id

    db.close()
    engine.dispose()

def test_the_correction_is_stored_against_the_named_season(show):
    library_service, seasons, server_id, library_id, item_id = show

    library_service.set_season_tmdb_match(server_id, library_id, item_id, 2,
                                          tmdb_id=225634, tmdb_season_number=1)

    corrected = seasons.get_season(library_id, item_id, 2)
    assert (corrected.tmdb_id_override, corrected.tmdb_season_number_override) == (225634, 1)
    assert seasons.get_season(library_id, item_id, 1).tmdb_id_override is None

def test_a_resync_does_not_clobber_it(show):
    library_service, seasons, server_id, library_id, item_id = show
    library_service.set_season_tmdb_match(server_id, library_id, item_id, 2,
                                          tmdb_id=225634, tmdb_season_number=1)

    seasons.create_or_update([
        LibrarySeason(show_id=item_id, library_id=library_id, external_id="s2",
                      season_number=2, title="Season 2", tmdb_id=299939)
    ])

    corrected = seasons.get_season(library_id, item_id, 2)
    assert (corrected.tmdb_id_override, corrected.tmdb_season_number_override) == (225634, 1)

def test_clearing_the_series_clears_the_number_with_it(show):
    library_service, seasons, server_id, library_id, item_id = show
    library_service.set_season_tmdb_match(server_id, library_id, item_id, 2,
                                          tmdb_id=225634, tmdb_season_number=1)

    library_service.set_season_tmdb_match(server_id, library_id, item_id, 2,
                                          tmdb_id=None, tmdb_season_number=1)

    cleared = seasons.get_season(library_id, item_id, 2)
    assert cleared.tmdb_id_override is None
    assert cleared.tmdb_season_number_override is None

def test_a_season_the_show_does_not_have_is_not_found(show):
    library_service, _, server_id, library_id, item_id = show

    assert library_service.set_season_tmdb_match(server_id, library_id, item_id, 9,
                                                 tmdb_id=225634, tmdb_season_number=1) is None
