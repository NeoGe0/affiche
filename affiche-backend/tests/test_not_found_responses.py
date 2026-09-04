from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.service_configuration.model.service_configuration import (
    ServiceConfiguration,
    ServiceType,
)
from affiche.app.service_configuration.service.configuration_repository import ConfigurationRepository
from affiche.config.database import SessionLocal

MISSING_ID = 999_999

def _seed_server(name: str, with_library: bool = True):
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name=name, type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        server_id = server.id
        library_id = None
        if with_library:
            LibraryService(session).create(Library(
                media_server_id=server_id, external_id=f"sec-{name}", name="Movies",
                type="movie", language="en", enabled=True,
            ))
        session.commit()
        if with_library:
            library_id = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server_id))[0].id
        return server_id, library_id
    finally:
        session.close()

def _enable_a_provider():
    session = SessionLocal()
    try:
        ConfigurationRepository(session).save(ServiceConfiguration(
            name="tvmaze", type=ServiceType.PROVIDER, token="", url="", enabled=True,
        ))
        session.commit()
    finally:
        session.close()

def _server_exists(server_id: int) -> bool:
    session = SessionLocal()
    try:
        return MediaServerPersistenceConnector(session).get(server_id) is not None
    finally:
        session.close()

def _libraries_of(server_id: int) -> list:
    session = SessionLocal()
    try:
        return LibraryService(session).find_libraries(LibrarySearch(media_server_id=server_id))
    finally:
        session.close()

def test_unknown_library_returns_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, _ = _seed_server("nf-lib")

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries/{MISSING_ID}")

        assert resp.status_code == 404
        assert str(MISSING_ID) in resp.json()["detail"]

def test_library_of_another_server_returns_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        _, library_id = _seed_server("nf-owner")
        other_server_id, _ = _seed_server("nf-other", with_library=False)

        resp = client.get(f"/affiche/media-servers/{other_server_id}/libraries/{library_id}")

        assert resp.status_code == 404

def test_every_library_scoped_listing_404s_for_unknown_library(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, _ = _seed_server("nf-listings")
        base = f"/affiche/media-servers/{server_id}/libraries/{MISSING_ID}"

        for path in ("", "/items", "/items/counts", "/items/alpha-index", "/trash"):
            resp = client.get(base + path)
            assert resp.status_code == 404, f"GET {base + path} → {resp.status_code}"

        resp = client.post(base + "/trash/empty")
        assert resp.status_code == 404

def test_unknown_item_returns_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed_server("nf-item")

        resp = client.get(
            f"/affiche/media-servers/{server_id}/libraries/{library_id}"
            f"/items/{MISSING_ID}/seasons"
        )

        assert resp.status_code == 404
        assert str(MISSING_ID) in resp.json()["detail"]

def test_applying_a_poster_to_an_unknown_item_returns_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed_server("nf-apply")
        _enable_a_provider()

        resp = client.post(
            f"/affiche/media-servers/{server_id}/libraries/{library_id}"
            f"/items/{MISSING_ID}/posters",
            json={"poster_url": "http://example.invalid/poster.jpg"},
        )

        assert resp.status_code == 404
        assert str(MISSING_ID) in resp.json()["detail"]

def test_syncing_an_unknown_item_returns_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed_server("nf-sync-item")

        resp = client.post(
            f"/affiche/media-servers/{server_id}/libraries/{library_id}"
            f"/items/{MISSING_ID}/sync"
        )

        assert resp.status_code == 404
        assert str(MISSING_ID) in resp.json()["detail"]

def test_delete_media_server_persists(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed_server("nf-delete")
        assert _server_exists(server_id)

        resp = client.delete(f"/affiche/media-servers/{server_id}")

        assert resp.status_code == 204
        assert not _server_exists(server_id), "media server was not actually deleted"
        assert _libraries_of(server_id) == [], "libraries should cascade with their server"

def test_delete_unknown_media_server_returns_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        resp = client.delete(f"/affiche/media-servers/{MISSING_ID}")

        assert resp.status_code == 404
