from fastapi.testclient import TestClient

import affiche.main  # noqa: F401  -- import first; `container` alone hits a circular import
from affiche.app.mediaserver.library.model import LibrarySearch
from affiche.config.dependencies import container

LIB_ID = 901
ITEM_ID = 902
SEASON = 3

ITEM_URL = f"/affiche/libraries/{LIB_ID}/items/{ITEM_ID}/poster"
SEASON_URL = f"/affiche/libraries/{LIB_ID}/items/{ITEM_ID}/seasons/{SEASON}/poster"

IMMUTABLE = "private, max-age=31536000, immutable"
REVALIDATE = "private, max-age=60, must-revalidate"

def test_versioned_url_is_immutable(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, b"jpegbytes")
        version = container.file_store.version(LIB_ID, ITEM_ID)

        resp = client.get(ITEM_URL, params={"v": version})
        assert resp.status_code == 200
        assert resp.content == b"jpegbytes"
        assert resp.headers["cache-control"] == IMMUTABLE

def test_versioned_season_url_is_immutable(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, b"seasonbytes", season_number=SEASON)
        version = container.file_store.version(LIB_ID, ITEM_ID, season_number=SEASON)

        resp = client.get(SEASON_URL, params={"v": version})
        assert resp.status_code == 200
        assert resp.content == b"seasonbytes"
        assert resp.headers["cache-control"] == IMMUTABLE

def test_unversioned_url_revalidates_instead(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, b"jpegbytes")

        first = client.get(ITEM_URL)
        assert first.status_code == 200
        assert first.headers["cache-control"] == REVALIDATE
        etag = first.headers["etag"]

        second = client.get(ITEM_URL, headers={"If-None-Match": etag})
        assert second.status_code == 304
        assert second.content == b""

def test_stale_version_is_not_immutable_and_serves_new_bytes(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, b"old-poster")
        stale = container.file_store.version(LIB_ID, ITEM_ID)

        container.file_store.save(LIB_ID, ITEM_ID, b"new-poster-different-size")

        resp = client.get(ITEM_URL, params={"v": stale})
        assert resp.status_code == 200
        assert resp.content == b"new-poster-different-size"
        assert resp.headers["cache-control"] == REVALIDATE

def test_stale_etag_serves_the_new_poster(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, b"old-poster")
        stale_etag = client.get(ITEM_URL).headers["etag"]

        container.file_store.save(LIB_ID, ITEM_ID, b"new-poster-different-size")

        resp = client.get(ITEM_URL, headers={"If-None-Match": stale_etag})
        assert resp.status_code == 200
        assert resp.content == b"new-poster-different-size"
        assert resp.headers["etag"] != stale_etag

def test_weak_and_multi_value_if_none_match_are_honoured(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.save(LIB_ID, ITEM_ID, b"jpegbytes")
        etag = client.get(ITEM_URL).headers["etag"]

        assert client.get(ITEM_URL, headers={"If-None-Match": f"W/{etag}"}).status_code == 304
        assert client.get(ITEM_URL, headers={"If-None-Match": f'"other", {etag}'}).status_code == 304
        assert client.get(ITEM_URL, headers={"If-None-Match": '"other"'}).status_code == 200

def test_missing_poster_is_404_not_a_cached_empty_response(authenticated_app):
    with TestClient(authenticated_app) as client:
        container.file_store.delete(LIB_ID, ITEM_ID)

        resp = client.get(ITEM_URL)
        assert resp.status_code == 404
        assert "etag" not in resp.headers

def test_version_changes_when_the_poster_is_rewritten(authenticated_app):
    container.file_store.save(LIB_ID, ITEM_ID, b"first")
    first = container.file_store.version(LIB_ID, ITEM_ID)

    container.file_store.save(LIB_ID, ITEM_ID, b"second-with-a-different-length")
    second = container.file_store.version(LIB_ID, ITEM_ID)

    assert first is not None and second is not None
    assert first != second

    container.file_store.delete(LIB_ID, ITEM_ID)
    assert container.file_store.version(LIB_ID, ITEM_ID) is None

def test_listing_hands_the_client_the_version_it_must_send(authenticated_app):
    from affiche.config.database import SessionLocal
    from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
    from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
    from affiche.app.mediaserver.library.service.library_service import LibraryService
    from affiche.app.mediaserver.library.model import Library
    from affiche.app.mediaserver.library.connector.library_item_entity import LibraryItemEntity

    with TestClient(authenticated_app) as client:
        session = SessionLocal()
        try:
            server = MediaServerPersistenceConnector(session).create(MediaServer(
                name="S", type=MediaServerType.PLEX, url="http://x", token="t",
            ))
            session.flush()
            LibraryService(session).create(Library(
                media_server_id=server.id, external_id="sec-c", name="Movies",
                type="movie", language="en", enabled=True,
            ))
            session.commit()
            lib = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server.id))[0]
            item = LibraryItemEntity(external_id="cache-me", library_id=lib.id, title="A",
                                     type="movie", processed=True)
            session.add(item)
            session.commit()
            server_id, lib_id, item_id = server.id, lib.id, item.id
        finally:
            session.close()

        container.file_store.save(lib_id, item_id, b"jpegbytes")

        listed = client.get(f"/affiche/media-servers/{server_id}/libraries/{lib_id}/items")
        assert listed.status_code == 200
        payload = next(i for i in listed.json()["items"] if i["id"] == item_id)

        assert payload["has_poster"] is True
        version = payload["poster_version"]
        assert version, "the listing must hand the client a version to put in the poster URL"

        poster = client.get(f"/affiche/libraries/{lib_id}/items/{item_id}/poster",
                            params={"v": version})
        assert poster.status_code == 200
        assert poster.headers["cache-control"] == IMMUTABLE
