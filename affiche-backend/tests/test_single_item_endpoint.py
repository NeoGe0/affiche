from fastapi.testclient import TestClient

from affiche.config.database import SessionLocal
from affiche.config.dependencies import container
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity

def _seed():
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name="S", type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        LibraryService(session).create(Library(
            media_server_id=server.id, external_id="sec-1", name="Movies",
            type="movie", language="en", enabled=True,
        ))
        session.commit()
        lib = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server.id))[0]
        item = LibraryItemEntity(external_id="a", library_id=lib.id, title="Alien", type="movie",
                                 processed=False, tmdb_id=348)
        session.add(item)
        session.commit()
        return server.id, lib.id, item.id
    finally:
        session.close()

def test_returns_the_item_with_the_same_derived_fields_as_the_listing(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, lib_id, item_id = _seed()
        container.file_store.save(lib_id, item_id, b"jpegbytes")

        resp = client.get(
            f"/affiche/media-servers/{server_id}/libraries/{lib_id}/items/{item_id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == item_id
        assert body["title"] == "Alien"
        assert body["has_poster"] is True
        assert body["poster_version"] is not None

        container.file_store.delete(lib_id, item_id)

def test_unknown_item_is_a_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, lib_id, _ = _seed()

        resp = client.get(
            f"/affiche/media-servers/{server_id}/libraries/{lib_id}/items/999999")

        assert resp.status_code == 404

def test_counts_and_alpha_index_still_win_over_the_id_route(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, lib_id, _ = _seed()
        base = f"/affiche/media-servers/{server_id}/libraries/{lib_id}/items"

        assert client.get(f"{base}/counts").status_code == 200
        assert client.get(f"{base}/alpha-index").status_code == 200
