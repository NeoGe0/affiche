from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibraryItem, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config.database import SessionLocal

ITEM_COUNT = 12

def _seed(name: str):
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name=name, type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        server_id = server.id
        service = LibraryService(session)
        service.create(Library(
            media_server_id=server_id, external_id=f"sec-{name}", name="Movies",
            type="movie", language="en", enabled=True,
        ))
        session.commit()
        library_id = service.find_libraries(LibrarySearch(media_server_id=server_id))[0].id
        service.create_or_update_items_batch([
            LibraryItem(external_id=f"{name}-{i}", library_id=library_id,
                        title=f"Movie {i:02d}", type="movie")
            for i in range(ITEM_COUNT)
        ])
        return server_id, library_id
    finally:
        session.close()

def _items_url(server_id: int, library_id: int) -> str:
    return f"/affiche/media-servers/{server_id}/libraries/{library_id}/items"

def test_zero_limit_is_rejected_rather_than_returning_everything(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-zero")

        resp = client.get(_items_url(server_id, library_id), params={"page_size": 0})

        assert resp.status_code == 422

def test_negative_limit_is_rejected_rather_than_returning_everything(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-neg")

        resp = client.get(_items_url(server_id, library_id), params={"page_size": -1})

        assert resp.status_code == 422

def test_negative_page_is_rejected(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-negoff")

        resp = client.get(_items_url(server_id, library_id), params={"page": -1})

        assert resp.status_code == 422

def test_a_normal_page_still_pages(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-ok")

        resp = client.get(_items_url(server_id, library_id), params={"page_size": 5, "page": 0})

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 5
        assert body["total"] == ITEM_COUNT

def test_total_pages_is_a_ceiling(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-pages")

        body = client.get(_items_url(server_id, library_id), params={"page_size": 5}).json()

        assert body["total"] == ITEM_COUNT
        assert body["total_pages"] == 3

def test_an_empty_listing_reports_zero_pages_not_one(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-empty")

        body = client.get(_items_url(server_id, library_id),
                          params={"search": "nothing-matches-this"}).json()

        assert body["total"] == 0
        assert body["total_pages"] == 0

def test_a_large_limit_is_allowed_because_jump_to_letter_needs_it(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-big")

        resp = client.get(_items_url(server_id, library_id), params={"page_size": 10_000})

        assert resp.status_code == 200
        assert len(resp.json()["items"]) == ITEM_COUNT

def test_trash_listing_has_the_same_bounds(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("paging-trash")
        trash = f"/affiche/media-servers/{server_id}/libraries/{library_id}/trash"

        assert client.get(trash, params={"page_size": 0}).status_code == 422
        assert client.get(trash, params={"page": -1}).status_code == 422
        assert client.get(trash, params={"page_size": 5}).status_code == 200
