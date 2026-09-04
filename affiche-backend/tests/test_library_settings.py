import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.config import Base
from affiche.config.library_config import DEFAULT_PROVIDER_ORDER

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

@pytest.fixture
def library_id(db) -> int:
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S", type=MediaServerType.PLEX, url="http://x", token="t",
    ))
    db.flush()
    library_service = LibraryService(db)
    library_service.create(Library(
        media_server_id=server.id, external_id="lib-1", name="Movies",
        type="movie", language="en", enabled=True,
    ))
    db.flush()
    lib_id = library_service.find_libraries(LibrarySearch(media_server_id=server.id))[0].id
    LibrarySettingsService(db).delete_settings(lib_id)
    db.commit()
    return lib_id

def test_get_or_default_returns_defaults_and_persists_nothing(db, library_id):
    service = LibrarySettingsService(db)

    settings = service.get_settings_or_default(library_id)

    assert settings.library_id == library_id
    assert settings.upload_enabled is True
    assert settings.provider_order == DEFAULT_PROVIDER_ORDER
    assert settings.overlay_options is None
    assert settings.text_options is None
    assert service.get_settings(library_id) is None

def test_get_or_default_returns_existing_row(db, library_id):
    service = LibrarySettingsService(db)
    service.partial_update_settings(library_id, {"upload_enabled": False})

    settings = service.get_settings_or_default(library_id)
    assert settings.upload_enabled is False

def test_partial_update_creates_row_when_missing(db, library_id):
    service = LibrarySettingsService(db)

    result = service.partial_update_settings(library_id, {"upload_enabled": False})

    assert result.upload_enabled is False
    assert result.provider_order == DEFAULT_PROVIDER_ORDER
    persisted = service.get_settings(library_id)
    assert persisted is not None
    assert persisted.upload_enabled is False

def test_partial_update_existing_row_changes_only_given_field(db, library_id):
    service = LibrarySettingsService(db)
    service.partial_update_settings(library_id, {"track_episodes": True})

    service.partial_update_settings(library_id, {"upload_enabled": False})

    settings = service.get_settings(library_id)
    assert settings.upload_enabled is False
    assert settings.track_episodes is True

def test_partial_update_clears_the_style_columns_with_an_explicit_null(db, library_id):
    service = LibrarySettingsService(db)
    service.partial_update_settings(library_id, {"overlay_options": {"border_px": 42},
                                                 "text_options": {"all_caps": True},
                                                 "upload_enabled": False})

    service.partial_update_settings(library_id, {"overlay_options": None,
                                                 "text_options": None,
                                                 "upload_enabled": None})

    settings = service.get_settings(library_id)
    assert settings.overlay_options is None
    assert settings.text_options is None
    assert settings.upload_enabled is False

def test_track_collections_survives_the_round_trip(authenticated_app):
    from fastapi.testclient import TestClient
    from affiche.config.database import SessionLocal

    with TestClient(authenticated_app) as client:
        session = SessionLocal()
        try:
            server = MediaServerPersistenceConnector(session).create(MediaServer(
                name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
            session.flush()
            server_id = server.id
            LibraryService(session).create(Library(
                media_server_id=server_id, external_id="sec-9", name="Movies",
                type="movie", language="en", enabled=True))
            session.commit()
            library_id = LibraryService(session).find_libraries(LibrarySearch(media_server_id=server_id))[0].id
        finally:
            session.close()

        base = f"/affiche/media-servers/{server_id}/libraries/{library_id}/settings"

        assert client.get(base).json()["track_collections"] is False
        assert client.patch(base, json={"track_collections": True}).json()["track_collections"] is True
        assert client.get(base).json()["track_collections"] is True

        assert client.patch(base, json={"overlay_options": {"border_px": 42}}).json()[
            "overlay_options"] == {"border_px": 42}
        assert client.patch(base, json={"overlay_options": None}).json()["overlay_options"] is None
        assert client.get(base).json()["overlay_options"] is None

        client.patch(base, json={"overlay_options": {"border_px": 7}})
        assert client.patch(base, json={"enabled": True}).json()["overlay_options"] == {"border_px": 7}

def _server_and_library(db, enabled=True):
    server = MediaServerPersistenceConnector(db).create(MediaServer(
        name="S2", type=MediaServerType.PLEX, url="http://y", token="t",
    ))
    db.flush()
    library_service = LibraryService(db)
    library_service.create(Library(
        media_server_id=server.id, external_id="lib-2", name="Shows",
        type="show", language="en", enabled=enabled,
    ))
    db.commit()
    library = library_service.find_libraries(LibrarySearch(media_server_id=server.id))[0]
    return server.id, library.id

def test_set_enabled_writes_the_library_row(db):
    server_id, library_id = _server_and_library(db)
    service = LibrarySettingsService(db)

    assert service.set_enabled(server_id, library_id, False) is False

    assert service.is_enabled(server_id, library_id) is False

def test_a_disabled_library_drops_out_of_the_processing_query(db):
    server_id, library_id = _server_and_library(db)
    LibrarySettingsService(db).set_enabled(server_id, library_id, False)

    found = LibraryService(db).find_libraries(
        LibrarySearch(media_server_id=server_id, enabled=True))

    assert [lib.id for lib in found] == []

def test_the_settings_patch_is_what_disables_a_library(authenticated_app):
    from fastapi.testclient import TestClient
    from affiche.config.database import SessionLocal

    with TestClient(authenticated_app) as client:
        session = SessionLocal()
        try:
            server = MediaServerPersistenceConnector(session).create(MediaServer(
                name="S3", type=MediaServerType.PLEX, url="http://z", token="t"))
            session.flush()
            server_id = server.id
            LibraryService(session).create(Library(
                media_server_id=server_id, external_id="en-1", name="Movies",
                type="movie", language="en", enabled=True))
            session.commit()
            library_id = LibraryService(session).find_libraries(
                LibrarySearch(media_server_id=server_id))[0].id
        finally:
            session.close()

        base = f"/affiche/media-servers/{server_id}/libraries/{library_id}/settings"

        assert client.get(base).json()["enabled"] is True

        body = client.patch(base, json={"enabled": False, "upload_enabled": False}).json()
        assert body["enabled"] is False
        assert body["upload_enabled"] is False
        assert client.get(base).json()["enabled"] is False

        session = SessionLocal()
        try:
            found = LibraryService(session).find_libraries(
                LibrarySearch(media_server_id=server_id, enabled=True))
            assert [lib.id for lib in found] == []
        finally:
            session.close()

        assert client.patch(base, json={"enabled": True}).json()["enabled"] is True
