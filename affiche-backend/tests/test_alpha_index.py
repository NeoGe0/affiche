import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.connector.alchemy_library_connector import (
    AlchemyLibraryConnector,
    bucket_letter,
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

def test_bucket_letter():
    assert bucket_letter("The Matrix") == "T"
    assert bucket_letter("avatar") == "A"
    assert bucket_letter("300") == "#"
    assert bucket_letter("") == "#"
    assert bucket_letter(None) == "#"
    assert bucket_letter("  Batman") == "B"

def test_letter_offsets_align_with_listing(db, library_id):
    connector = AlchemyLibraryConnector(db)
    titles = ["Avatar", "300", "Alien", "Batman", "Aliens", "Zodiac", "Predator"]
    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id=f"e{i}", title=t, type="movie")
        for i, t in enumerate(titles)
    ])

    items = connector.find_items(LibraryItemSearch(library_id=library_id))
    offsets = connector.letter_offsets(LibraryItemSearch(library_id=library_id))

    for letter, offset in offsets:
        assert bucket_letter(items[offset].title) == letter
        assert all(bucket_letter(items[j].title) != letter for j in range(offset))

    assert {letter for letter, _ in offsets} == {bucket_letter(i.title) for i in items}
    assert len(offsets) == len({letter for letter, _ in offsets})

def test_letter_offsets_respect_processed_filter(db, library_id):
    connector = AlchemyLibraryConnector(db)
    connector.create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id="a", title="Alien", type="movie"),
        LibraryItem(library_id=library_id, external_id="b", title="Batman", type="movie"),
    ])
    batman = next(i for i in connector.find_items(LibraryItemSearch(library_id=library_id)) if i.title == "Batman")
    batman.processed = True
    connector.update_item(batman)

    processed = connector.letter_offsets(LibraryItemSearch(library_id=library_id, processed=True))
    assert [letter for letter, _ in processed] == ["B"]
