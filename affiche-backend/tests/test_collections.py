from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.collections.library_collection_service import (
    CollectionWriteError,
    LibraryCollectionService,
)
from affiche.app.mediaserver.library.collections.model.library_collection import (
    LibraryCollectionSearch,
)
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config import Base
from affiche.config.exceptions.exceptions import LibraryCollectionNotFoundException

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
def library(db):
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    service = LibraryService(db)
    service.create(Library(media_server_id=server.id, external_id="sec-1", name="Movies",
                           type="movie", language="en", enabled=True))
    db.commit()
    stored_library = service.find_libraries(LibrarySearch(media_server_id=server.id))[0]

    service.create_or_update_items_batch([
        LibraryItem(library_id=stored_library.id, external_id=external, title=title, type="movie")
        for external, title in [("100", "Alien"), ("200", "Aliens"), ("300", "Dune")]
    ])
    db.commit()
    return server.id, stored_library

def _entry(external_id: str, title: str, members: list[str], **overrides) -> dict:
    return {'external_id': external_id, 'title': title, 'member_external_ids': members, **overrides}

def _items(db, library_id: int) -> dict[str, LibraryItem]:
    return {item.title: item
            for item in LibraryService(db).find_items(LibraryItemSearch(library_id=library_id))}

def test_sync_stores_collections_and_their_members(db, library):
    server_id, lib = library
    service = LibraryCollectionService(db)

    service.sync_collections(lib.id, [_entry("c1", "Alien Saga", ["100", "200"], child_count=2)])

    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))
    assert [(c.title, c.child_count) for c in stored] == [("Alien Saga", 2)]
    members = service.get_members(server_id, lib.id, stored[0].id)
    assert sorted(m.title for m in members) == ["Alien", "Aliens"]

def test_members_affiche_has_not_synced_are_dropped_not_invented(db, library):
    server_id, lib = library
    service = LibraryCollectionService(db)

    service.sync_collections(lib.id, [_entry("c1", "Mixed", ["100", "999"], child_count=2)])

    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]
    assert stored.child_count == 2
    assert [m.title for m in service.get_members(server_id, lib.id, stored.id)] == ["Alien"]

def test_a_resync_replaces_membership_rather_than_accumulating(db, library):
    server_id, lib = library
    service = LibraryCollectionService(db)
    service.sync_collections(lib.id, [_entry("c1", "Saga", ["100", "200"])])

    service.sync_collections(lib.id, [_entry("c1", "Saga", ["300"])])

    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]
    assert [m.title for m in service.get_members(server_id, lib.id, stored.id)] == ["Dune"]

def test_a_collection_the_server_no_longer_has_is_soft_deleted(db, library):
    _, lib = library
    service = LibraryCollectionService(db)
    service.sync_collections(lib.id, [_entry("c1", "Gone", ["100"]), _entry("c2", "Kept", ["200"])])

    service.sync_collections(lib.id, [_entry("c2", "Kept", ["200"])])

    listed = service.find_collections(LibraryCollectionSearch(library_id=lib.id))
    assert [c.title for c in listed] == ["Kept"]
    trashed = service.find_collections(LibraryCollectionSearch(library_id=lib.id, deleted=True))
    assert [c.title for c in trashed] == ["Gone"]

def test_a_sync_does_not_clear_the_lock_or_poster_state(db, library):
    server_id, lib = library
    service = LibraryCollectionService(db)
    service.sync_collections(lib.id, [_entry("c1", "Saga", ["100"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]
    service.set_locked(server_id, lib.id, stored.id, True)

    service.sync_collections(lib.id, [_entry("c1", "Saga Renamed", ["100"])])

    refreshed = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]
    assert refreshed.title == "Saga Renamed"
    assert refreshed.locked is True

def test_drop_empty_keeps_only_the_collections_with_a_member_here(db, library):
    _, lib = library
    service = LibraryCollectionService(db)

    service.sync_collections(lib.id, [
        _entry("c1", "Ours", ["100"]),
        _entry("c2", "Someone else's", ["9001", "9002"]),
    ], drop_empty=True)

    listed = service.find_collections(LibraryCollectionSearch(library_id=lib.id))
    assert [c.title for c in listed] == ["Ours"]

def test_without_drop_empty_an_empty_collection_is_kept(db, library):
    _, lib = library
    service = LibraryCollectionService(db)

    service.sync_collections(lib.id, [_entry("c1", "Empty on purpose", [])])

    assert [c.title for c in service.find_collections(LibraryCollectionSearch(library_id=lib.id))] \
           == ["Empty on purpose"]

def _writing_service(db, connector: MagicMock) -> LibraryCollectionService:
    factory = MagicMock()
    factory.get.return_value = connector
    return LibraryCollectionService(db, connector_factory=factory)

def _connector(**overrides) -> MagicMock:
    connector = MagicMock()
    connector.create_collection.return_value = "new-1"
    connector.rename_collection.return_value = True
    connector.delete_collection.return_value = True
    connector.add_to_collection.return_value = True
    connector.remove_from_collection.return_value = True
    for name, value in overrides.items():
        getattr(connector, name).return_value = value
    return connector

def test_create_writes_to_the_media_server_then_records_the_row(db, library):
    server_id, lib = library
    connector = _connector()
    service = _writing_service(db, connector)
    items = _items(db, lib.id)

    created = service.create_collection(server_id, lib.id, "New Saga",
                                        [items["Alien"].id, items["Dune"].id])

    connector.create_collection.assert_called_once()
    _, title, external_ids = connector.create_collection.call_args.args
    assert title == "New Saga"
    assert sorted(external_ids) == ["100", "300"]
    assert created.external_id == "new-1"
    assert sorted(m.title for m in service.get_members(server_id, lib.id, created.id)) == \
           ["Alien", "Dune"]

def test_nothing_is_recorded_when_the_media_server_refuses_the_create(db, library):
    server_id, lib = library
    service = _writing_service(db, _connector(create_collection=None))
    items = _items(db, lib.id)

    with pytest.raises(CollectionWriteError):
        service.create_collection(server_id, lib.id, "Doomed", [items["Alien"].id])

    assert service.find_collections(LibraryCollectionSearch(library_id=lib.id)) == []

def test_a_refused_rename_leaves_the_stored_title_alone(db, library):
    server_id, lib = library
    service = _writing_service(db, _connector(rename_collection=False))
    service.sync_collections(lib.id, [_entry("c1", "Original", ["100"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]

    with pytest.raises(CollectionWriteError):
        service.rename_collection(server_id, lib.id, stored.id, "New")

    assert service.get_collection(server_id, lib.id, stored.id).title == "Original"

def test_a_refused_delete_leaves_the_row(db, library):
    server_id, lib = library
    service = _writing_service(db, _connector(delete_collection=False))
    service.sync_collections(lib.id, [_entry("c1", "Stays", ["100"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]

    with pytest.raises(CollectionWriteError):
        service.delete_collection(server_id, lib.id, stored.id)

    assert service.get_collection(server_id, lib.id, stored.id).title == "Stays"

def test_delete_removes_the_row_and_its_membership(db, library):
    server_id, lib = library
    service = _writing_service(db, _connector())
    service.sync_collections(lib.id, [_entry("c1", "Doomed", ["100", "200"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]

    service.delete_collection(server_id, lib.id, stored.id)

    with pytest.raises(LibraryCollectionNotFoundException):
        service.get_collection(server_id, lib.id, stored.id)
    assert len(_items(db, lib.id)) == 3

def test_adding_and_removing_members_writes_both_sides(db, library):
    server_id, lib = library
    connector = _connector()
    service = _writing_service(db, connector)
    service.sync_collections(lib.id, [_entry("c1", "Saga", ["100"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]
    items = _items(db, lib.id)

    assert service.add_items(server_id, lib.id, stored.id, [items["Dune"].id]) == 1
    assert sorted(m.title for m in service.get_members(server_id, lib.id, stored.id)) == \
           ["Alien", "Dune"]

    assert service.remove_items(server_id, lib.id, stored.id, [items["Alien"].id]) == 1
    assert [m.title for m in service.get_members(server_id, lib.id, stored.id)] == ["Dune"]

def test_a_refused_add_does_not_record_membership(db, library):
    server_id, lib = library
    service = _writing_service(db, _connector(add_to_collection=False))
    service.sync_collections(lib.id, [_entry("c1", "Saga", ["100"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]
    items = _items(db, lib.id)

    with pytest.raises(CollectionWriteError):
        service.add_items(server_id, lib.id, stored.id, [items["Dune"].id])

    assert [m.title for m in service.get_members(server_id, lib.id, stored.id)] == ["Alien"]

def test_items_from_another_library_are_not_added(db, library):
    server_id, lib = library
    connector = _connector()
    service = _writing_service(db, connector)
    service.sync_collections(lib.id, [_entry("c1", "Saga", ["100"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]

    assert service.add_items(server_id, lib.id, stored.id, [999999]) == 0
    connector.add_to_collection.assert_not_called()

def test_a_collection_is_not_reachable_through_another_library(db, library):
    server_id, lib = library
    library_service = LibraryService(db)
    library_service.create(Library(media_server_id=server_id, external_id="sec-2", name="Docs",
                                   type="movie", language="en", enabled=True))
    db.commit()
    other = next(l for l in library_service.find_libraries(LibrarySearch(media_server_id=server_id)) if l.name == "Docs")

    service = LibraryCollectionService(db)
    service.sync_collections(lib.id, [_entry("c1", "Saga", ["100"])])
    stored = service.find_collections(LibraryCollectionSearch(library_id=lib.id))[0]

    with pytest.raises(LibraryCollectionNotFoundException):
        service.get_collection(server_id, other.id, stored.id)

def test_the_collection_endpoints_are_session_gated():
    with TestClient(main_module.app) as client:
        assert client.get("/affiche/media-servers/1/libraries/1/collections").status_code == 401
        assert client.post("/affiche/media-servers/1/libraries/1/collections",
                           json={"title": "X", "item_ids": [1]}).status_code == 401

def test_create_rejects_an_empty_title_or_selection(authenticated_app):
    with TestClient(authenticated_app) as client:
        base = "/affiche/media-servers/1/libraries/1/collections"
        assert client.post(base, json={"title": "", "item_ids": [1]}).status_code == 422
        assert client.post(base, json={"title": "X", "item_ids": []}).status_code == 422
