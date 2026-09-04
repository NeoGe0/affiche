from fastapi.testclient import TestClient

import affiche.main as main_module
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
        with_poster = LibraryItemEntity(external_id="a", library_id=lib.id, title="A", type="movie", processed=False)
        without_poster = LibraryItemEntity(external_id="b", library_id=lib.id, title="B", type="movie", processed=False)
        session.add_all([with_poster, without_poster])
        session.commit()
        return server.id, lib.id, with_poster.id, without_poster.id
    finally:
        session.close()

def test_has_poster_reflects_stored_file(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, lib_id, item_with, item_without = _seed()
        container.file_store.save(lib_id, item_with, b"jpegbytes")

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries/{lib_id}/items")
        assert resp.status_code == 200
        by_id = {i["id"]: i for i in resp.json()["items"]}

        assert by_id[item_with]["has_poster"] is True
        assert by_id[item_without]["has_poster"] is False

        assert client.get(
            f"/affiche/libraries/{lib_id}/items/{item_with}/poster"
        ).status_code == 200
        assert client.get(
            f"/affiche/libraries/{lib_id}/items/{item_without}/poster"
        ).status_code == 404

        container.file_store.delete(lib_id, item_with)
