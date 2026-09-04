from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.connector.alchemy_library_connector import AlchemyLibraryConnector
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

def test_get_unuploaded_items_filters(db, library_id):
    connector = AlchemyLibraryConnector(db)
    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="a", title="Uploaded", type="movie"),
        LibraryItem(library_id=library_id, external_id="b", title="Unuploaded", type="movie"),
        LibraryItem(library_id=library_id, external_id="c", title="Unprocessed", type="movie"),
        LibraryItem(library_id=library_id, external_id="d", title="Deleted", type="movie"),
    ])
    by_ext = {i.external_id: i for i in connector.find_items(LibraryItemSearch(library_id=library_id))}

    up = by_ext["a"]; up.processed = True; up.poster_uploaded_at = datetime.now(timezone.utc)
    connector.update_item(up)
    un = by_ext["b"]; un.processed = True
    connector.update_item(un)
    de = by_ext["d"]; de.processed = True; de.deleted_at = datetime.now(timezone.utc)
    connector.update_item(de)

    result = connector.find_items(LibraryItemSearch(library_id=library_id, processed=True, uploaded=False))

    assert [i.external_id for i in result] == ["b"]

def test_resync_preserves_poster_hash(db, library_id):
    connector = AlchemyLibraryConnector(db)
    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="a", title="Movie", type="movie"),
    ])
    item = connector.find_items(LibraryItemSearch(library_id=library_id))[0]
    item.processed = True
    item.poster_hash = "abc123"
    item.poster_uploaded_at = datetime.now(timezone.utc)
    connector.update_item(item)

    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="a", title="Movie (renamed)", type="movie"),
    ])

    resynced = connector.find_items(LibraryItemSearch(library_id=library_id))[0]
    assert resynced.title == "Movie (renamed)"
    assert resynced.poster_hash == "abc123"
    assert resynced.poster_uploaded_at is not None
