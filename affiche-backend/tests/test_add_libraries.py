import pytest
from fastapi.testclient import TestClient

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.config.app_settings_store import AppSettingsStore
from affiche.config.database import SessionLocal

ADD_URL = "/affiche/media-servers/{id}/available-libraries"

@pytest.fixture(autouse=True)
def _restore_shared_state():
    before = AppSettingsStore().get()
    created: list[int] = []
    yield created

    session = SessionLocal()
    try:
        connector = MediaServerPersistenceConnector(session)
        for server_id in created:
            connector.delete(server_id)
        session.commit()
    finally:
        session.close()
    AppSettingsStore().save(before)

def _create_server(created: list[int]) -> int:
    session = SessionLocal()
    try:
        server = MediaServerPersistenceConnector(session).create(MediaServer(
            name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
        session.commit()
        created.append(server.id)
        return server.id
    finally:
        session.close()

def _library(external_id: str, name: str) -> dict:
    return {"id": external_id, "name": name, "type": "movie",
            "item_count": 0, "language": "en"}

def _added(server_id: int) -> dict:
    session = SessionLocal()
    try:
        return {lib.name: lib for lib in LibraryService(session).find_libraries(
            LibrarySearch(media_server_id=server_id))}
    finally:
        session.close()

def _settings(library_id: int):
    session = SessionLocal()
    try:
        return LibrarySettingsService(session).get_settings(library_id)
    finally:
        session.close()

def test_the_batch_is_created_with_the_settings_the_request_carries(authenticated_app, _restore_shared_state):
    with TestClient(authenticated_app) as client:
        server_id = _create_server(_restore_shared_state)

        response = client.post(ADD_URL.format(id=server_id), json={
            "libraries": [_library("ext-1", "Movies"), _library("ext-2", "Kids")],
            "new_library_enabled": False,
            "new_library_upload_enabled": False,
            "new_library_provider_order": ["mediux", "tmdb"],
        })

        assert response.status_code == 201
        added = _added(server_id)
        assert set(added) == {"Movies", "Kids"}
        for library in added.values():
            assert library.enabled is False
            settings = _settings(library.id)
            assert settings.upload_enabled is False
            assert settings.provider_order == ["mediux", "tmdb"]

def test_omitted_settings_keep_what_was_chosen_last_time(authenticated_app, _restore_shared_state):
    with TestClient(authenticated_app) as client:
        server_id = _create_server(_restore_shared_state)
        AppSettingsStore().partial_update({"new_library_upload_enabled": False,
                                           "new_library_provider_order": ["fanart"]})

        client.post(ADD_URL.format(id=server_id), json={
            "libraries": [_library("ext-3", "Docs")],
            "new_library_enabled": True,
        })

        library = _added(server_id)["Docs"]
        assert library.enabled is True
        settings = _settings(library.id)
        assert settings.upload_enabled is False
        assert settings.provider_order == ["fanart"]

def test_the_choice_is_remembered_for_the_next_add(authenticated_app, _restore_shared_state):
    with TestClient(authenticated_app) as client:
        server_id = _create_server(_restore_shared_state)

        client.post(ADD_URL.format(id=server_id), json={
            "libraries": [_library("ext-4", "Anime")],
            "new_library_enabled": False,
            "new_library_provider_order": ["tvdb"],
        })

        stored = AppSettingsStore().get()
        assert stored.new_library_enabled is False
        assert stored.new_library_provider_order == ["tvdb"]

        client.post(ADD_URL.format(id=server_id), json={
            "libraries": [_library("ext-5", "Shorts")],
        })

        assert _added(server_id)["Shorts"].enabled is False

def test_an_unknown_server_is_a_404_and_writes_nothing(authenticated_app, _restore_shared_state):
    with TestClient(authenticated_app) as client:
        before = AppSettingsStore().get().new_library_enabled

        response = client.post(ADD_URL.format(id=9999), json={
            "libraries": [_library("ext-6", "Nope")],
            "new_library_enabled": not before,
        })

        assert response.status_code == 404
        assert AppSettingsStore().get().new_library_enabled is before
