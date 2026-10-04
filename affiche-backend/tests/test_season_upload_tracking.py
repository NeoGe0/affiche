from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
import affiche.app.mediaserver.service.media_server_poster_service as poster_module
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    Library,
    LibraryItem,
    LibraryItemSearch,
    LibrarySearch,
    SeasonPosterState,
)
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.service.poster_resolver import PosterSource
from affiche.app.mediaserver.service.poster_uploader import PosterUploader
from affiche.config import Base

UPLOADED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
SERVER_HASH = "what-the-server-holds"

class Show:

    def __init__(self, session_factory):
        self.session_factory = session_factory
        db = session_factory()
        server = MediaServerPersistenceConnector(db).create(MediaServer(
            name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
        db.flush()
        library_service = LibraryService(db)
        library_service.create(Library(media_server_id=server.id, external_id="sec-1", name="Shows",
                                       type="show", language="en", enabled=True))
        db.commit()
        self.server_id = server.id
        self.library = library_service.find_libraries(LibrarySearch(media_server_id=server.id))[0]
        library_service.create_or_update_items_batch(
            [LibraryItem(library_id=self.library.id, external_id="show", title="Monster",
                         type="show")])
        db.commit()
        self.item_id = library_service.find_items(LibraryItemSearch(library_id=self.library.id))[0].id
        LibrarySeasonService(db).create_or_update([
            LibrarySeason(show_id=self.item_id, library_id=self.library.id, external_id=f"s{n}",
                          season_number=n, title=f"Season {n}")
            for n in (1, 2)
        ])
        db.commit()
        db.close()

    def set_item(self, **state):
        db = self.session_factory()
        repo = LibraryRepository(db)
        item = repo.get_library_item(self.library.id, self.item_id)
        repo.create_or_update_item(item.model_copy(update=state))
        db.close()

    def set_season(self, number: int, **state):
        db = self.session_factory()
        seasons = LibrarySeasonService(db)
        seasons.update_seasons([seasons.get_season(self.library.id, self.item_id, number)],
                               SeasonPosterState(**state))
        db.close()

    def season(self, number: int) -> LibrarySeason:
        db = self.session_factory()
        try:
            return LibrarySeasonService(db).get_season(self.library.id, self.item_id, number)
        finally:
            db.close()

    def uploaded(self):
        self.set_item(processed=True, poster_uploaded_at=UPLOADED_AT, poster_hash=SERVER_HASH)
        self.set_season(1, processed=True, poster_uploaded_at=UPLOADED_AT, poster_hash=SERVER_HASH)

@pytest.fixture
def show(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'seasons.db'}")
    Base.metadata.create_all(engine)
    yield Show(sessionmaker(bind=engine))
    engine.dispose()

def _uploader(show: Show) -> PosterUploader:
    file_store = MagicMock()
    file_store.exists.return_value = True
    file_store.path.return_value = "/tmp/poster.jpg"
    file_store.digest.return_value = SERVER_HASH
    return PosterUploader(file_store=file_store, session_factory=show.session_factory)

def _pushed(connector) -> list[str]:
    return sorted(call.args[0] for call in connector.upload_poster.call_args_list)

def test_the_upload_run_pushes_a_season_generated_after_its_show_was_uploaded(show):
    show.uploaded()
    show.set_season(2, processed=True)
    connector = MagicMock()
    connector.upload_poster.return_value = True

    _uploader(show).upload_library_posters(show.library, connector)

    assert _pushed(connector) == ["s2"]
    assert show.season(2).poster_uploaded_at is not None
    assert show.season(2).poster_hash == SERVER_HASH

def test_the_upload_run_pushes_the_seasons_of_a_show_it_uploads(show):
    show.set_item(processed=True)
    show.set_season(1, processed=True)
    show.set_season(2, processed=True)
    connector = MagicMock()
    connector.upload_poster.return_value = True

    _uploader(show).upload_library_posters(show.library, connector)

    assert _pushed(connector) == ["s1", "s2", "show"]

def test_a_season_that_was_never_generated_is_not_pushed(show):
    show.uploaded()
    connector = MagicMock()

    _uploader(show).upload_library_posters(show.library, connector)

    connector.upload_poster.assert_not_called()
    assert show.season(2).poster_hash is None

def test_a_season_whose_push_failed_is_still_waiting(show):
    show.uploaded()
    show.set_season(2, processed=True)
    connector = MagicMock()
    connector.upload_poster.return_value = False

    _uploader(show).upload_library_posters(show.library, connector)

    assert show.season(2).poster_uploaded_at is None

def test_a_resync_leaves_the_upload_stamp_alone(show):
    show.uploaded()
    db = show.session_factory()
    LibrarySeasonService(db).create_or_update([
        LibrarySeason(show_id=show.item_id, library_id=show.library.id, external_id="s1",
                      season_number=1, title="Season 1, renamed")])
    db.close()

    assert show.season(1).title == "Season 1, renamed"
    assert show.season(1).poster_uploaded_at is not None

def _poster_service(show: Show, monkeypatch) -> LibraryPosterService:
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = object.__new__(LibraryPosterService)
    svc._session_factory = show.session_factory
    svc._decorator = MagicMock()
    svc._decorator.decorate_poster.return_value = b"poster-bytes"
    svc._decorator.style_fingerprint.return_value = "style"
    svc._file_store = MagicMock()
    svc._file_store.save.return_value = "/tmp/poster.jpg"
    svc._uploader = PosterUploader(file_store=svc._file_store, session_factory=show.session_factory)
    svc._resolver = MagicMock()
    svc._resolver.resolve_season_poster.return_value = PosterSource(
        source="http://poster", styled=True, provider="tmdb")
    svc._get_connector = lambda media_server_id: MagicMock()
    svc._get_server_poster_settings = lambda media_server_id: MagicMock()
    return svc

def test_generating_without_uploading_leaves_the_season_waiting(show, monkeypatch):
    show.uploaded()
    svc = _poster_service(show, monkeypatch)
    db = show.session_factory()
    seasons = LibrarySeasonService(db)
    item = LibraryRepository(db).get_library_item(show.library.id, show.item_id)

    assert svc._process_season_poster(seasons, db, show.season(1), item, "http://poster",
                                      MagicMock(), upload=False) is True
    db.close()

    assert show.season(1).poster_uploaded_at is None
    assert show.season(1).poster_hash == SERVER_HASH

def test_the_generate_run_picks_up_a_new_season_of_a_processed_show(show, monkeypatch):
    show.uploaded()
    svc = _poster_service(show, monkeypatch)
    svc._process_item = MagicMock()

    svc._process_library(show.server_id, show.library, upload=False)

    svc._process_item.assert_not_called()
    assert show.season(2).processed is True
    asked = [call.args[1].season_number for call in svc._resolver.resolve_season_poster.call_args_list]
    assert asked == [2]

def test_a_new_season_with_no_artwork_does_not_fail_its_show(show, monkeypatch):
    show.uploaded()
    svc = _poster_service(show, monkeypatch)
    svc._resolver.resolve_season_poster.return_value = None

    svc._process_library(show.server_id, show.library, upload=False)

    db = show.session_factory()
    item = LibraryRepository(db).get_library_item(show.library.id, show.item_id)
    db.close()
    assert item.processed is True
    assert item.error_message is None
    assert show.season(2).processed is False

def test_a_locked_show_keeps_its_new_season_untouched(show, monkeypatch):
    show.uploaded()
    show.set_item(processed=True, poster_uploaded_at=UPLOADED_AT, poster_hash=SERVER_HASH,
                  locked=True)
    svc = _poster_service(show, monkeypatch)

    svc._process_library(show.server_id, show.library, upload=False)

    assert show.season(2).processed is False

def test_known_season_ids_are_told_from_new_ones(show):
    db = show.session_factory()
    known = LibrarySeasonService(db).find_known_external_ids(show.library.id, ["s1", "s2", "s3"])
    db.close()

    assert known == {"s1", "s2"}
