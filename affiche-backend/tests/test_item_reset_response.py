from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401  (initialises routers/DI)
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config.database import SessionLocal
from affiche.config.dependencies import container, get_poster_sync_service

def _seed():
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name="S", type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        LibraryService(session).create(Library(
            media_server_id=server.id, external_id="sec-reset", name="Movies",
            type="movie", language="en", enabled=True,
        ))
        session.commit()
        library = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server.id))[0]
        item = LibraryItemEntity(external_id="a", library_id=library.id, title="A",
                                 type="movie", processed=True)
        session.add(item)
        session.commit()
        return server.id, library.id, item.id
    finally:
        session.close()

class _FakeResetService:

    def reset_item_posters(self, media_server_id, library_id, item_id):
        container.file_store.save(library_id, item_id, b"the-servers-own-artwork")
        session = SessionLocal()
        try:
            item = session.get(LibraryItemEntity, item_id)
            item.processed = False
            session.commit()
        finally:
            session.close()

def test_reset_returns_the_item_with_the_restored_poster(authenticated_app):
    authenticated_app.dependency_overrides[get_poster_sync_service] = lambda: _FakeResetService()
    try:
        with TestClient(authenticated_app) as client:
            server_id, library_id, item_id = _seed()

            resp = client.post(
                f"/affiche/media-servers/{server_id}/libraries/{library_id}"
                f"/items/{item_id}/posters/reset"
            )

            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == item_id
            assert body["processed"] is False
            assert body["has_poster"] is True
            assert body["poster_version"] is not None

            container.file_store.delete(library_id, item_id)
    finally:
        authenticated_app.dependency_overrides.pop(get_poster_sync_service, None)
