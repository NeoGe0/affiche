import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.library.service.library_service import LibraryService
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.app.mediaserver.service.media_server_poster_service import (
    GLOBAL_STYLE,
    LibraryPosterService,
)
from affiche.app.style_profile.service.style_profile_service import (
    DuplicateProfileNameError,
    StyleProfileService,
)
from affiche.config import Base
from affiche.config.exceptions.exceptions import StyleProfileNotFoundException

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
        name="S", type=MediaServerType.PLEX, url="http://x", token="t"))
    db.flush()
    LibraryService(db).create(Library(
        media_server_id=server.id, external_id="lib-1", name="Anime",
        type="show", language="en", enabled=True))
    db.commit()
    return LibraryService(db).find_libraries(LibrarySearch(media_server_id=server.id))[0].id

def test_a_profile_stores_the_full_option_bag_not_the_partial_one_given(db):
    profile = StyleProfileService(db).create_profile("Kids", overlay_options={"border_px": 42})

    assert profile.overlay_options["border_px"] == 42
    assert "border_color" in profile.overlay_options

def test_an_unusable_option_bag_is_refused_rather_than_stored(db):
    with pytest.raises(Exception):
        StyleProfileService(db).create_profile("Broken", overlay_options={"border_px": "many"})

def test_names_are_unique_regardless_of_case(db):
    service = StyleProfileService(db)
    service.create_profile("Anime")

    with pytest.raises(DuplicateProfileNameError):
        service.create_profile("  anime  ")

def test_renaming_a_profile_to_its_own_name_is_not_a_conflict(db):
    service = StyleProfileService(db)
    profile = service.create_profile("Anime")

    assert service.update_profile(profile.id, {"name": "Anime"}).name == "Anime"

def test_update_clears_a_bag_when_sent_null_but_leaves_an_absent_one_alone(db):
    service = StyleProfileService(db)
    profile = service.create_profile("Anime", overlay_options={"border_px": 42},
                                     text_options={"all_caps": True})

    updated = service.update_profile(profile.id, {"overlay_options": None})

    assert updated.overlay_options is None
    assert updated.text_options["all_caps"] is True

def test_deleting_an_unknown_profile_is_a_404(db):
    with pytest.raises(StyleProfileNotFoundException):
        StyleProfileService(db).delete_profile(999)

def _assign(db, library_id: int, profile_id) -> None:
    LibrarySettingsService(db).partial_update_settings(
        library_id, {"style_profile_id": profile_id})

def _style_for(db, library_id: int):
    svc = object.__new__(LibraryPosterService)
    return svc._get_library_style(db, library_id)

def test_an_assigned_profile_supplies_the_style(db, library_id):
    profile = StyleProfileService(db).create_profile("Kids", overlay_options={"border_px": 42})
    _assign(db, library_id, profile.id)

    assert _style_for(db, library_id).overlay_options.border_px == 42

def test_a_profile_wins_over_the_librarys_own_inline_columns(db, library_id):
    profile = StyleProfileService(db).create_profile("Kids", overlay_options={"border_px": 42})
    LibrarySettingsService(db).partial_update_settings(library_id, {
        "overlay_options": {"border_px": 7}, "style_profile_id": profile.id})

    assert _style_for(db, library_id).overlay_options.border_px == 42

def test_clearing_the_profile_falls_back_to_the_inline_columns(db, library_id):
    profile = StyleProfileService(db).create_profile("Kids", overlay_options={"border_px": 42})
    LibrarySettingsService(db).partial_update_settings(library_id, {
        "overlay_options": {"border_px": 7}, "style_profile_id": profile.id})

    _assign(db, library_id, None)

    assert _style_for(db, library_id).overlay_options.border_px == 7

def test_deleting_a_profile_hands_its_libraries_back_to_the_global_style(db, library_id):
    service = StyleProfileService(db)
    profile = service.create_profile("Kids", overlay_options={"border_px": 42})
    _assign(db, library_id, profile.id)

    service.delete_profile(profile.id)

    assert LibrarySettingsService(db).get_settings(library_id).style_profile_id is None
    assert _style_for(db, library_id) == GLOBAL_STYLE

def test_library_count_reports_how_many_libraries_use_a_profile(db, library_id):
    service = StyleProfileService(db)
    profile = service.create_profile("Kids")
    assert service.count_libraries_using(profile.id) == 0

    _assign(db, library_id, profile.id)

    assert service.count_libraries_using(profile.id) == 1

def test_profile_crud_round_trip(authenticated_app):
    with TestClient(authenticated_app) as client:
        created = client.post("/affiche/style-profiles",
                              json={"name": "Anime", "text_options": {"all_caps": True}})
        assert created.status_code == 201
        profile_id = created.json()["id"]
        assert created.json()["library_count"] == 0

        assert client.post("/affiche/style-profiles", json={"name": "Anime"}).status_code == 409

        listed = client.get("/affiche/style-profiles").json()
        assert [p["name"] for p in listed] == ["Anime"]

        renamed = client.patch(f"/affiche/style-profiles/{profile_id}", json={"name": "Anime Dark"})
        assert renamed.json()["name"] == "Anime Dark"
        assert renamed.json()["text_options"]["all_caps"] is True

        assert client.delete(f"/affiche/style-profiles/{profile_id}").status_code == 204
        assert client.get("/affiche/style-profiles").json() == []
        assert client.patch(f"/affiche/style-profiles/{profile_id}", json={"name": "X"}).status_code == 404
