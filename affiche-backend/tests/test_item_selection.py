import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.item_selection import resolve_selection
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

def _server(db, name: str, libraries: dict[str, list[str]]) -> tuple[int, dict[str, LibraryItem]]:
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name=name, type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    service = LibraryService(db)
    items: dict[str, LibraryItem] = {}

    for index, (library_name, titles) in enumerate(libraries.items()):
        service.create(Library(media_server_id=server.id, external_id=f"{name}-{index}",
                               name=library_name, type="movie", language="en",
                               enabled=True))
        db.commit()
        library = next(lib for lib in service.find_libraries(LibrarySearch(media_server_id=server.id)) if lib.name == library_name)
        service.create_or_update_items_batch([
            LibraryItem(library_id=library.id, external_id=f"{library.id}-{i}", title=title,
                        type="movie")
            for i, title in enumerate(titles)
        ])
        db.commit()
        for item in service.find_items(LibraryItemSearch(library_id=library.id)):
            items[item.title] = item

    return server.id, items

def test_a_selection_is_grouped_by_library(db):
    server_id, items = _server(db, "Plex", {"Movies": ["Alien", "Aliens"], "Docs": ["Koyaanisqatsi"]})
    selection = [items["Alien"].id, items["Koyaanisqatsi"].id]

    resolved = resolve_selection(LibraryRepository(db), server_id, selection)

    assert sorted(library.name for library, _ in resolved) == ["Docs", "Movies"]
    by_name = {library.name: [i.title for i in group] for library, group in resolved}
    assert by_name == {"Movies": ["Alien"], "Docs": ["Koyaanisqatsi"]}

def test_a_selection_cannot_reach_another_servers_items(db):
    _, mine = _server(db, "Plex", {"Movies": ["Alien"]})
    other_id, theirs = _server(db, "Jellyfin", {"Shows": ["Twin Peaks"]})

    resolved = resolve_selection(LibraryRepository(db), other_id,
                                 [mine["Alien"].id, theirs["Twin Peaks"].id])

    assert [(lib.name, [i.title for i in group]) for lib, group in resolved] == \
           [("Shows", ["Twin Peaks"])]

def test_an_empty_selection_resolves_to_nothing(db):
    server_id, _ = _server(db, "Plex", {"Movies": ["Alien"]})

    assert resolve_selection(LibraryRepository(db), server_id, []) == []

def test_unknown_ids_are_simply_absent(db):
    server_id, items = _server(db, "Plex", {"Movies": ["Alien"]})

    resolved = resolve_selection(LibraryRepository(db), server_id, [items["Alien"].id, 9999])

    assert [i.title for _, group in resolved for i in group] == ["Alien"]

def test_bulk_lock_sets_every_selected_item(db):
    server_id, items = _server(db, "Plex", {"Movies": ["Alien", "Aliens"], "Docs": ["Koyaanisqatsi"]})
    service = LibraryService(db)
    selection = [items["Alien"].id, items["Koyaanisqatsi"].id]

    assert service.set_items_locked(server_id, selection, True) == 2

    locked = service.find_items(LibraryItemSearch(
        library_ids=[items[t].library_id for t in items], locked=True))
    assert sorted(i.title for i in locked) == ["Alien", "Koyaanisqatsi"]

def test_bulk_lock_reports_only_what_actually_changed(db):
    server_id, items = _server(db, "Plex", {"Movies": ["Alien", "Aliens"]})
    service = LibraryService(db)
    service.set_items_locked(server_id, [items["Alien"].id], True)

    changed = service.set_items_locked(server_id, [items["Alien"].id, items["Aliens"].id], True)

    assert changed == 1

def test_bulk_unlock_clears_the_selection(db):
    server_id, items = _server(db, "Plex", {"Movies": ["Alien", "Aliens"]})
    service = LibraryService(db)
    ids = [items["Alien"].id, items["Aliens"].id]
    service.set_items_locked(server_id, ids, True)

    assert service.set_items_locked(server_id, ids, False) == 2
    assert service.find_items(LibraryItemSearch(library_ids=[items["Alien"].library_id],
                                                locked=True)) == []

def test_bulk_lock_refuses_another_servers_items(db):
    my_id, mine = _server(db, "Plex", {"Movies": ["Alien"]})
    other_id, _ = _server(db, "Jellyfin", {"Shows": ["Twin Peaks"]})
    service = LibraryService(db)
    alien = mine["Alien"]

    assert service.set_items_locked(other_id, [alien.id], True) == 0
    assert service.get_library_item(my_id, alien.library_id, alien.id).locked is False

def test_the_selection_endpoints_reject_an_empty_selection(authenticated_app):
    with TestClient(authenticated_app) as client:
        for path in ("generate", "upload", "reset"):
            resp = client.post(f"/affiche/media-servers/1/libraries/items/selection/posters/{path}",
                               json={"item_ids": []})
            assert resp.status_code == 422, path

def test_the_selection_endpoints_are_session_gated():
    with TestClient(main_module.app) as client:
        resp = client.post("/affiche/media-servers/1/libraries/items/selection/posters/generate",
                           json={"item_ids": [1]})
        assert resp.status_code == 401
