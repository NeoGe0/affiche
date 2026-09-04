from fastapi.testclient import TestClient

import affiche.main as main_module
from affiche.config.database import SessionLocal
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibrarySearch

def _seed_server_and_library():
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name="S", type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        LibraryService(session).create(Library(
            media_server_id=server.id, external_id="sec-3", name="Movies",
            type="movie", language="en", enabled=True,
        ))
        session.commit()
        lib = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server.id))[0]
        return server.id, lib.id
    finally:
        session.close()

def test_libraries_path_returns_db_list_not_remote(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, db_library_id = _seed_server_and_library()

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries")

        assert resp.status_code == 200
        libs = resp.json()
        assert len(libs) == 1
        lib = libs[0]
        assert lib["media_server_id"] == server_id
        assert lib["id"] == db_library_id
        assert isinstance(lib["id"], int)
        assert lib["name"] == "Movies"

def test_settings_reachable_by_db_id(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, db_library_id = _seed_server_and_library()

        resp = client.get(
            f"/affiche/media-servers/{server_id}/libraries/{db_library_id}/settings"
        )

        assert resp.status_code == 200
        assert resp.json()["library_id"] == db_library_id
