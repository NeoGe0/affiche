from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.app.mediaserver.service.media_server_poster_service as poster_module
from affiche.api.schemas.library import (
    ErrorCause,
    PROCESSED_NO_POSTER_ERROR,
    _effective_error,
    _error_cause,
)
from affiche.app.mediaserver.library.model import ItemStatusFilter, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibraryItem
from affiche.app.mediaserver.library.connector.alchemy_library_connector import AlchemyLibraryConnector
from affiche.app.mediaserver.service.media_server_poster_service import (
    GLOBAL_STYLE,
    LibraryPosterService,
    _season_failure_message,
)
from affiche.config import Base
from affiche.app.mediaserver.library.model import LibraryItemSearch, SortDir

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
def library_id(db) -> int:
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    LibraryService(db).create(Library(
        media_server_id=server.id, external_id="lib-1", name="Movies",
        type="movie", language="en", enabled=True,
    ))
    db.commit()
    return LibraryService(db).find_libraries(LibrarySearch(media_server_id=server.id))[0].id

def _item(**kwargs) -> LibraryItem:
    base = dict(id=1, library_id=1, external_id="x", title="T", type="movie")
    base.update(kwargs)
    return LibraryItem(**base)

def test_effective_error_prefers_persisted_message():
    item = _item(processed=True, error_message="boom")
    assert _effective_error(item, has_poster=False) == "boom"
    assert _effective_error(item, has_poster=True) == "boom"

def test_effective_error_flags_processed_without_poster():
    assert _effective_error(_item(processed=True), has_poster=False) == PROCESSED_NO_POSTER_ERROR

def test_effective_error_none_for_healthy_or_pending_items():
    assert _effective_error(_item(processed=True), has_poster=True) is None
    assert _effective_error(_item(processed=False), has_poster=False) is None

def test_error_cause_points_at_a_mismatch_when_only_tmdb_is_known():
    assert _error_cause(_item(tmdb_id=123), "boom") == ErrorCause.IDENTIFIER_MISMATCH
    assert _error_cause(_item(), "boom") == ErrorCause.IDENTIFIER_MISMATCH

def test_error_cause_absent_when_the_item_is_properly_identified_or_healthy():
    assert _error_cause(_item(tmdb_id=123, imdb_id="tt1"), "boom") is None
    assert _error_cause(_item(tmdb_id=123, tvdb_id=7), "boom") is None
    assert _error_cause(_item(), None) is None

def test_status_filter_expands_to_the_listing_predicates():
    def predicates(status):
        s = LibraryItemSearch(library_id=1, status=status)
        return s.processed, s.has_error

    assert predicates(None) == (None, None)
    assert predicates(ItemStatusFilter.UNPROCESSED) == (False, False)
    assert predicates(ItemStatusFilter.ERRORS) == (None, True)

def test_has_error_filter(db, library_id):
    connector = AlchemyLibraryConnector(db)
    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="ok", title="Clean", type="movie"),
        LibraryItem(library_id=library_id, external_id="bad", title="Broken", type="movie"),
    ])
    broken = next(i for i in connector.find_items(LibraryItemSearch(library_id=library_id)) if i.external_id == "bad")
    broken.error_message = "No poster found from any provider"
    connector.update_item(broken)

    errored = connector.find_items(LibraryItemSearch(library_id=library_id, has_error=True))
    assert [i.external_id for i in errored] == ["bad"]
    assert connector.count_items(LibraryItemSearch(library_id=library_id, has_error=True)) == 1

    pending = connector.find_items(LibraryItemSearch(library_id=library_id, processed=False, has_error=False))
    assert [i.external_id for i in pending] == ["ok"]

def _service_with_mocks():
    svc = object.__new__(LibraryPosterService)
    svc._decorator = MagicMock()
    svc._decorator.decorate_poster.return_value = b"poster-bytes"
    svc._file_store = MagicMock()
    svc._file_store.save.return_value = "/tmp/poster.jpg"
    return svc

def test_mark_item_failed_sets_message():
    svc = _service_with_mocks()
    repo = MagicMock()
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie")

    svc._mark_item_failed(repo, item, "boom")

    assert item.error_message == "boom"
    assert item.processed is False
    repo.create_or_update_item.assert_called_once_with(item)

def test_season_failure_message_lists_sorted_numbers():
    assert _season_failure_message([3, 1]) == "Season poster generation failed for season(s): 1, 3"

def test_process_series_seasons_reports_failed_and_raised_seasons():
    svc = object.__new__(LibraryPosterService)
    season_service = MagicMock()
    season_service.get_item_seasons.return_value = [
        MagicMock(season_number=1), MagicMock(season_number=2), MagicMock(season_number=3),
    ]

    def fake_process(_ss, _session, season, *_args):
        if season.season_number == 1:
            return True
        if season.season_number == 2:
            return False
        raise RuntimeError("boom")

    svc._process_season = fake_process
    item = LibraryItem(id=1, library_id=1, external_id="x", title="Show", type="show")

    failed = svc._process_series_seasons(season_service, MagicMock(), item, ["tmdb"], [""], GLOBAL_STYLE,
                                         MagicMock(), False)

    assert sorted(failed) == [2, 3]

def test_process_item_poster_clears_error_on_success(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie",
                       error_message="previously failed")

    assert svc._process_item_poster(repo, MagicMock(), item, "http://poster", connector, upload=False) is True
    assert item.error_message is None
