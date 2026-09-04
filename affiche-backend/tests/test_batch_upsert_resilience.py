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

def _item(library_id, ext, title="T"):
    return LibraryItem(library_id=library_id, external_id=ext, title=title, type="movie")

def test_bad_row_is_isolated_good_rows_persist(db, library_id):
    connector = AlchemyLibraryConnector(db)
    BAD_LIBRARY_ID = 999999

    connector.create_or_update_items_batch([
        _item(library_id, "good-1"),
        _item(BAD_LIBRARY_ID, "bad"),
        _item(library_id, "good-2"),
    ])

    externals = {i.external_id for i in connector.find_items(LibraryItemSearch(library_id=library_id))}
    assert externals == {"good-1", "good-2"}

def test_session_usable_after_bad_batch(db, library_id):
    connector = AlchemyLibraryConnector(db)
    connector.create_or_update_items_batch([_item(999999, "bad")])

    connector.create_or_update_items_batch([_item(library_id, "later")])
    assert {i.external_id for i in connector.find_items(LibraryItemSearch(library_id=library_id))} == {"later"}

def test_happy_path_persists_all(db, library_id):
    connector = AlchemyLibraryConnector(db)
    connector.create_or_update_items_batch([
        _item(library_id, "a"), _item(library_id, "b"), _item(library_id, "c"),
    ])
    assert len(connector.find_items(LibraryItemSearch(library_id=library_id))) == 3
