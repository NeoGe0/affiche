from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config.database import SessionLocal
from affiche.config.dependencies import container

def test_delete_library_removes_the_whole_tree(tmp_path):
    store = FileStoreService(root_dir=tmp_path)
    store.save(1, 10, b"movie poster")
    store.save(1, 11, b"show poster")
    store.save(1, 11, b"season poster", season_number=2)

    assert store.delete_library(1) is True

    assert store.version(1, 10) is None
    assert store.version(1, 11) is None
    assert store.version(1, 11, season_number=2) is None
    assert not (tmp_path / "libraries" / "1").exists()

def test_delete_library_leaves_other_libraries_alone(tmp_path):
    store = FileStoreService(root_dir=tmp_path)
    store.save(1, 10, b"doomed")
    store.save(2, 10, b"keep me")

    store.delete_library(1)

    assert store.version(2, 10) is not None
    assert store.fetch(2, 10) == b"keep me"

def test_delete_library_takes_thumbnails_too(tmp_path):
    store = FileStoreService(root_dir=tmp_path, thumbnailer=lambda data: b"thumb")
    store.save(1, 10, b"poster")
    assert store._sharded_path(1, 10, None, thumb=True).exists()

    store.delete_library(1)

    assert not store._sharded_path(1, 10, None, thumb=True).exists()

def test_delete_library_is_a_noop_when_nothing_is_stored(tmp_path):
    assert FileStoreService(root_dir=tmp_path).delete_library(999) is False

def _seed(name: str):
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name=name, type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        server_id = server.id
        LibraryService(session).create(Library(
            media_server_id=server_id, external_id=f"sec-{name}", name="Movies",
            type="movie", language="en", enabled=True,
        ))
        session.commit()
        library_id = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server_id))[0].id
    finally:
        session.close()

    container.file_store.save(library_id, 1, b"poster bytes")
    assert container.file_store.version(library_id, 1) is not None
    return server_id, library_id

def test_deleting_a_library_deletes_its_posters(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("cleanup-lib")

        resp = client.delete(f"/affiche/media-servers/{server_id}/libraries/{library_id}")

        assert resp.status_code == 204
        assert container.file_store.version(library_id, 1) is None

def test_deleting_a_media_server_deletes_its_libraries_posters(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed("cleanup-server")

        resp = client.delete(f"/affiche/media-servers/{server_id}")

        assert resp.status_code == 204
        assert container.file_store.version(library_id, 1) is None
