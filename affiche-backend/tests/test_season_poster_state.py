import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    Library,
    LibraryItem,
    LibraryItemSearch,
    SeasonPosterState,
    LibrarySearch,
)
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config import Base

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture
def seasons(db):
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
    db.flush()
    library_service = LibraryService(db)
    library_service.create(Library(media_server_id=server.id, external_id="sec-1", name="Shows",
                                   type="show", language="en", enabled=True))
    db.commit()
    library = library_service.find_libraries(LibrarySearch(media_server_id=server.id))[0]
    library_service.create_or_update_items_batch(
        [LibraryItem(library_id=library.id, external_id="1", title="Show", type="show")])
    db.commit()
    show = library_service.find_items(LibraryItemSearch(library_id=library.id))[0]

    service = LibrarySeasonService(db)
    service.create_or_update([
        LibrarySeason(show_id=show.id, library_id=library.id, external_id=f"s{n}",
                      season_number=n, title=f"Season {n}")
        for n in (1, 2)
    ])
    db.commit()
    stored = service.get_item_seasons(library.id, show.id)
    service.update_seasons(stored, SeasonPosterState(
        processed=True, poster_hash="abc", poster_provider="tmdb", style_hash="style-1"))
    return service, library.id, show.id

def _state(service, library_id, show_id):
    return {s.season_number: s for s in service.get_item_seasons(library_id, show_id)}

def test_a_reset_clears_every_poster_column_at_once(seasons):
    service, library_id, show_id = seasons
    stored = list(_state(service, library_id, show_id).values())

    service.update_seasons(stored, SeasonPosterState(
        processed=False, poster_hash=None, poster_provider=None, style_hash=None))

    for season in _state(service, library_id, show_id).values():
        assert season.processed is False
        assert season.poster_hash is None
        assert season.poster_provider is None
        assert season.style_hash is None

def test_a_column_the_caller_did_not_name_is_left_alone(seasons):
    service, library_id, show_id = seasons
    stored = list(_state(service, library_id, show_id).values())

    service.update_seasons(stored, SeasonPosterState(poster_hash="rewritten"))

    season = _state(service, library_id, show_id)[1]
    assert season.poster_hash == "rewritten"
    assert season.processed is True
    assert season.poster_provider == "tmdb"
    assert season.style_hash == "style-1"

def test_only_the_named_seasons_are_written(seasons):
    service, library_id, show_id = seasons
    by_number = _state(service, library_id, show_id)

    service.update_seasons([by_number[1]], SeasonPosterState(processed=False))

    after = _state(service, library_id, show_id)
    assert after[1].processed is False
    assert after[2].processed is True

def test_an_empty_state_writes_nothing(seasons):
    service, library_id, show_id = seasons
    stored = list(_state(service, library_id, show_id).values())

    service.update_seasons(stored, SeasonPosterState())

    assert all(s.processed and s.poster_hash == "abc"
               for s in _state(service, library_id, show_id).values())

def test_no_seasons_is_not_an_error(seasons):
    service, _, _ = seasons

    service.update_seasons([], SeasonPosterState(processed=False))

def test_the_state_object_reports_only_what_was_named():
    assert SeasonPosterState(processed=True).changes() == {"processed": True}
    assert SeasonPosterState(poster_hash=None).changes() == {"poster_hash": None}
    assert SeasonPosterState().changes() == {}
