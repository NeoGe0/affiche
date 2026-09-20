from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import affiche.app.mediaserver.service.media_server_poster_service as poster_module
import affiche.app.mediaserver.service.poster_resetter as resetter_module
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    Library, LibraryItem, LibraryItemSearch, LibrarySearch, SortDir,
)
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.media_server_connector_protocol import ResetResult
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
from affiche.app.mediaserver.service.poster_uploader import PosterUploader
from affiche.config import Base

def _service():
    svc = object.__new__(LibraryPosterService)
    svc._decorator = MagicMock()
    svc._decorator.decorate_poster.return_value = b"poster-bytes"
    svc._file_store = MagicMock()
    svc._file_store.save.return_value = "/tmp/poster.jpg"
    svc._uploader = PosterUploader(file_store=svc._file_store, session_factory=MagicMock())
    svc._resetter = PosterResetter(file_store=svc._file_store, session_factory=MagicMock())
    return svc

def test_generating_a_poster_stamps_when(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    repo = MagicMock()
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie")
    before = datetime.now(timezone.utc)

    _service()._process_item_poster(repo, MagicMock(), item, "http://poster", MagicMock(), upload=False)

    assert repo.create_or_update_item.call_args.args[0].poster_generated_at >= before

def test_a_reset_clears_it(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    repo = MagicMock()
    connector = MagicMock()
    connector.reset_poster.return_value = ResetResult(True)
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie",
                       processed=True, poster_generated_at=datetime.now(timezone.utc))

    _service()._resetter.reset_poster(repo, item, connector)

    assert repo.create_or_update_item.call_args.args[0].poster_generated_at is None

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()

def test_the_listing_sorts_newest_poster_first_with_the_unknown_last(db):
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
    db.flush()
    LibraryService(db).create(Library(media_server_id=server.id, external_id="l", name="Films",
                                      type="movie", language="en", enabled=True))
    db.commit()
    library_id = LibraryService(db).find_libraries(LibrarySearch(media_server_id=server.id))[0].id
    LibraryService(db).create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id=f"e{i}", title=title, type="movie")
        for i, title in enumerate(["Alien", "Brazil", "Heat"])
    ])
    db.commit()
    items = {i.title: i for i in LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))}
    now = datetime.now(timezone.utc)
    for title, generated in [("Alien", now - timedelta(days=2)), ("Heat", now)]:
        items[title].poster_generated_at = generated
        LibraryRepository(db).create_or_update_item(items[title])

    listed = LibraryService(db).find_items(LibraryItemSearch(
        library_id=library_id, sort_by="poster_generated_at", sort_dir=SortDir.DESC))

    assert [i.title for i in listed] == ["Heat", "Alien", "Brazil"]
