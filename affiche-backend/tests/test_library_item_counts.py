from datetime import datetime, timezone

from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.config.database import SessionLocal
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity

def _seed(item_titles, deleted_titles=(), providers=None):
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name="S", type=MediaServerType.PLEX, url="http://x", token="t",
        ))
        session.flush()
        LibraryService(session).create(Library(
            media_server_id=server.id, external_id="sec-count", name="Movies",
            type="movie", language="en", enabled=True,
        ))
        session.commit()
        lib = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server.id))[0]

        session.add_all([
            LibraryItemEntity(external_id=f"live-{t}", library_id=lib.id, title=t,
                              type="movie", processed=False,
                              poster_provider=(providers or {}).get(t))
            for t in item_titles
        ])
        session.add_all([
            LibraryItemEntity(external_id=f"gone-{t}", library_id=lib.id, title=t,
                              type="movie", processed=False,
                              deleted_at=datetime.now(timezone.utc))
            for t in deleted_titles
        ])
        session.commit()
        return server.id, lib.id
    finally:
        session.close()

def test_library_list_counts_actual_items(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, _ = _seed(["A", "B", "C"])

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries")

        assert resp.status_code == 200
        [lib] = resp.json()
        assert lib["media_count"] == 3

def test_single_library_does_not_derive_a_count(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed(["A", "B"])

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries/{library_id}")

        assert resp.status_code == 200
        assert resp.json()["media_count"] is None

def test_trashed_items_are_not_counted(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, _ = _seed(["A", "B"], deleted_titles=["X", "Y", "Z"])

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries")

        [lib] = resp.json()
        assert lib["media_count"] == 2

def test_empty_library_counts_zero(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, _ = _seed([])

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries")

        [lib] = resp.json()
        assert lib["media_count"] == 0

def test_the_counts_endpoint_reports_a_bucket_per_provider(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed(["A", "B", "C", "D"],
                                      providers={"A": "tmdb", "B": "tmdb", "C": "server"})

        resp = client.get(
            f"/affiche/media-servers/{server_id}/libraries/{library_id}/items/counts")

        assert resp.status_code == 200
        assert resp.json()["providers"] == {"tmdb": 2, "server": 1, "none": 1}

def test_the_status_buckets_narrow_to_the_provider_the_listing_is_filtered_to(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed(["A", "B", "C"], providers={"A": "tmdb", "B": "mediux"})

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries/{library_id}"
                          f"/items/counts?provider=tmdb")

        body = resp.json()
        assert body["total"] == 1
        assert body["providers"] == {"tmdb": 1, "mediux": 1, "none": 1}

def test_the_listing_can_be_filtered_to_items_with_no_provenance(authenticated_app):
    with TestClient(authenticated_app) as client:
        server_id, library_id = _seed(["A", "B"], providers={"A": "tmdb"})

        resp = client.get(f"/affiche/media-servers/{server_id}/libraries/{library_id}"
                          f"/items?provider=none")

        assert [item["title"] for item in resp.json()["items"]] == ["B"]
