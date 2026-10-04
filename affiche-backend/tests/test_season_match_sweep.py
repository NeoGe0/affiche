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
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.season_match_service import SeasonMatchService
from affiche.config import Base
from affiche.external.poster.season_match import SeasonMatchSuggestion, missing_seasons
from affiche.external.poster.provider.base_provider import SeriesFacts, SeriesSeason

def _facts(*numbers):
    return SeriesFacts(id=299939, name="Monster: The Lizzie Borden Story",
                       seasons=[SeriesSeason(number=n) for n in numbers])

def test_a_library_season_tmdb_does_not_have_is_missing():
    assert missing_seasons(_facts(1), [1, 2, 3, 4]) == [2, 3, 4]

def test_an_entry_that_agrees_reports_nothing():
    assert missing_seasons(_facts(1, 2, 3), [1, 2, 3]) == []

def test_specials_are_ignored_on_both_sides():
    assert missing_seasons(_facts(0, 1), [0, 1]) == []

def test_an_unfetchable_entry_is_not_evidence():
    assert missing_seasons(None, [1, 2, 3]) == []

def test_numbering_the_catalogue_does_not_share_is_caught():
    assert missing_seasons(_facts(1, 2), [1, 5]) == [5]

class FakeAggregator:

    def __init__(self, tmdb_seasons=(1,), suggestion="ok"):
        self._tmdb_seasons = tmdb_seasons
        self._suggestion = suggestion
        self.described = 0
        self.suggested = []

    def describe_tmdb_series(self, tmdb_id):
        self.described += 1
        return _facts(*self._tmdb_seasons) if self._tmdb_seasons else None

    def suggest_season_match(self, show_title, season_number, tvdb_id=None):
        self.suggested.append(season_number)
        if self._suggestion is None:
            return None
        return SeasonMatchSuggestion(tmdb_id=225634, season_number=1,
                                     series_name="Monsters: The Lyle and Erik Menendez Story",
                                     reason="checked out")

@pytest.fixture
def library():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()

    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
    db.flush()
    services = LibraryService(db)
    services.create(Library(media_server_id=server.id, external_id="sec-1", name="Shows",
                            type="show", language="en", enabled=True))
    db.commit()
    lib = services.find_libraries(LibrarySearch(media_server_id=server.id))[0]

    def add_show(title, tmdb_id, tvdb_id, season_numbers):
        services.create_or_update_items_batch([LibraryItem(
            library_id=lib.id, external_id=title, title=title, type="show",
            tmdb_id=tmdb_id, tvdb_id=tvdb_id)])
        db.commit()
        item = next(i for i in services.find_items(LibraryItemSearch(library_id=lib.id))
                    if i.title == title)
        LibrarySeasonService(db).create_or_update([
            LibrarySeason(show_id=item.id, library_id=lib.id, external_id=f"{title}-s{n}",
                          season_number=n, title=f"Season {n}")
            for n in season_numbers])
        db.commit()
        return item

    yield factory, db, server.id, lib.id, add_show

    db.close()
    engine.dispose()

def _seasons(db, library_id, item_id):
    return {s.season_number: s
            for s in LibrarySeasonService(db).get_item_seasons(library_id, item_id)}

def test_a_suspect_show_gets_its_missing_seasons_corrected(library):
    factory, db, server_id, library_id, add_show = library
    show = add_show("Monster", "299939", "389492", [1, 2, 3, 4])
    aggregator = FakeAggregator(tmdb_seasons=(1,))

    report = SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id)

    assert (report.shows_suspect, report.resolved, report.unresolved) == (1, 3, 0)
    assert aggregator.suggested == [2, 3, 4]
    stored = _seasons(db, library_id, show.id)
    assert stored[2].tmdb_id_override == 225634
    assert stored[1].tmdb_id_override is None

def test_a_show_tmdb_agrees_with_costs_one_call_and_no_more(library):
    factory, _, server_id, library_id, add_show = library
    add_show("Severance", "95396", "371980", [1, 2])
    aggregator = FakeAggregator(tmdb_seasons=(1, 2))

    report = SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id)

    assert report.shows_suspect == 0
    assert aggregator.described == 1
    assert aggregator.suggested == []

def test_a_season_already_corrected_is_left_alone(library):
    factory, db, server_id, library_id, add_show = library
    show = add_show("Monster", "299939", "389492", [1, 2])
    seasons = LibrarySeasonService(db)
    seasons.set_tmdb_match(_seasons(db, library_id, show.id)[2].id, 111111, 1)
    aggregator = FakeAggregator(tmdb_seasons=(1,))

    report = SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id)

    assert aggregator.suggested == []
    assert report.shows_suspect == 0
    assert _seasons(db, library_id, show.id)[2].tmdb_id_override == 111111

def test_a_season_that_does_not_resolve_is_counted_not_guessed(library):
    factory, db, server_id, library_id, add_show = library
    show = add_show("Monster", "299939", "389492", [1, 2, 3])
    aggregator = FakeAggregator(tmdb_seasons=(1,), suggestion=None)

    report = SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id)

    assert (report.resolved, report.unresolved) == (0, 2)
    stored = _seasons(db, library_id, show.id)
    assert stored[2].tmdb_id_override is None and stored[3].tmdb_id_override is None

def test_a_show_without_a_tvdb_id_is_skipped(library):
    factory, _, server_id, library_id, add_show = library
    add_show("Monster", "299939", None, [1, 2])
    aggregator = FakeAggregator(tmdb_seasons=(1,))

    report = SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id)

    assert report.shows_suspect == 0
    assert aggregator.described == 0

def test_a_show_without_a_tmdb_id_is_skipped(library):
    factory, _, server_id, library_id, add_show = library
    add_show("Monster", None, "389492", [1, 2])
    aggregator = FakeAggregator(tmdb_seasons=(1,))

    report = SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id)

    assert report.shows_suspect == 0
    assert aggregator.described == 0

def test_one_failing_show_does_not_end_the_sweep(library):
    factory, db, server_id, library_id, add_show = library
    add_show("Explodes", "1", "2", [1, 2])
    good = add_show("Monster", "299939", "389492", [1, 2])

    class Exploding(FakeAggregator):
        def describe_tmdb_series(self, tmdb_id):
            if tmdb_id == 1:
                raise RuntimeError("tmdb is down for this one")
            return super().describe_tmdb_series(tmdb_id)

    aggregator = Exploding(tmdb_seasons=(1,))
    report = SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id)

    assert report.shows_scanned == 2
    assert report.resolved == 1
    assert _seasons(db, library_id, good.id)[2].tmdb_id_override == 225634

def test_cancelling_stops_the_sweep(library):
    factory, _, server_id, library_id, add_show = library
    for n in range(3):
        add_show(f"Show {n}", "299939", "389492", [1, 2])
    aggregator = FakeAggregator(tmdb_seasons=(1,))

    SeasonMatchService(factory, lambda _s: aggregator).fix_library_season_matches(
        server_id, library_id, cancel_check=lambda: True)

    assert aggregator.described == 0
