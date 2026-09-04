import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import (
    ItemStatusFilter, Library, LibraryItem, LibraryItemSearch,
    LibrarySearch,
)
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
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
def server_and_library(db) -> tuple[int, int]:
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    LibraryService(db).create(Library(
        media_server_id=server.id, external_id="lib-1", name="Movies",
        type="movie", language="en", enabled=True,
    ))
    db.commit()
    return server.id, LibraryService(db).find_libraries(LibrarySearch(media_server_id=server.id))[0].id

def _seed(db, library_id: int, titles: list[str]) -> dict[str, LibraryItem]:
    LibraryService(db).create_or_update_items_batch([
        LibraryItem(library_id=library_id, external_id=f"e{i}", title=title, type="movie")
        for i, title in enumerate(titles)
    ])
    db.commit()
    return {item.title: item
            for item in LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))}

def test_an_item_starts_unlocked(db, server_and_library):
    _, library_id = server_and_library
    items = _seed(db, library_id, ["Alien"])

    assert items["Alien"].locked is False

def test_locking_an_item_persists(db, server_and_library):
    server_id, library_id = server_and_library
    items = _seed(db, library_id, ["Alien"])

    updated = LibraryService(db).set_item_locked(server_id, library_id, items["Alien"].id, True)

    assert updated.locked is True
    assert LibraryService(db).get_library_item(
        server_id, library_id, items["Alien"].id).locked is True

def test_a_locked_item_is_excluded_from_the_generation_queue(db, server_and_library):
    _, library_id = server_and_library
    items = _seed(db, library_id, ["Alien", "Aliens"])
    service = LibraryService(db)
    service.set_item_locked(*server_and_library, items["Alien"].id, True)

    queued = service.find_items(LibraryItemSearch(library_id=library_id, processed=False,
                                                  locked=False))

    assert [item.title for item in queued] == ["Aliens"]

def test_a_locked_item_is_still_reset(db, server_and_library):
    _, library_id = server_and_library
    items = _seed(db, library_id, ["Alien", "Aliens"])
    service = LibraryService(db)
    repo = LibraryRepository(db)
    for item in items.values():
        item.processed = True
        repo.create_or_update_item(item)
    service.set_item_locked(*server_and_library, items["Alien"].id, True)

    queued = service.find_items(LibraryItemSearch(library_id=library_id, attempted=True))

    assert sorted(item.title for item in queued) == ["Alien", "Aliens"]

def test_a_sync_does_not_clear_the_lock(db, server_and_library):
    server_id, library_id = server_and_library
    items = _seed(db, library_id, ["Alien"])
    LibraryService(db).set_item_locked(server_id, library_id, items["Alien"].id, True)

    _seed(db, library_id, ["Alien"])

    assert LibraryService(db).get_library_item(
        server_id, library_id, items["Alien"].id).locked is True

def test_the_locked_filter_lists_exactly_the_locked_items(db, server_and_library):
    _, library_id = server_and_library
    items = _seed(db, library_id, ["Alien", "Aliens", "Blade Runner"])
    service = LibraryService(db)
    service.set_item_locked(*server_and_library, items["Alien"].id, True)
    service.set_item_locked(*server_and_library, items["Blade Runner"].id, True)

    listed = service.find_items(LibraryItemSearch(library_id=library_id,
                                                  status=ItemStatusFilter.LOCKED))

    assert sorted(item.title for item in listed) == ["Alien", "Blade Runner"]
    assert service.count_status_buckets(LibraryItemSearch(library_id=library_id)).locked == 2

def test_status_cannot_be_combined_with_the_predicate_it_expands_into(db, server_and_library):
    _, library_id = server_and_library

    with pytest.raises(ValueError):
        LibraryItemSearch(library_id=library_id, status=ItemStatusFilter.LOCKED, locked=False)
