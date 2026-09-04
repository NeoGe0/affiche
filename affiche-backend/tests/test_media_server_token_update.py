from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche.app.mediaserver.service import media_server_probe_service as probe_module
from affiche.app.events import internal_event_bus
from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity
from affiche.app.mediaserver.model.media_server import MediaServerType
from affiche.config.database import SessionLocal, init_db

OLD_TOKEN = "old-token-aaaaaaaa"
NEW_TOKEN = "new-token-bbbbbbbb"

def _seed_server(type_=MediaServerType.PLEX, token=OLD_TOKEN) -> int:
    init_db()
    session = SessionLocal()
    try:
        entity = MediaServerEntity(name="Seeded", type=type_, url="http://localhost:32400",
                                   token=token, enabled=True)
        session.add(entity)
        session.commit()
        return entity.id
    finally:
        session.close()

def _stored_token(server_id: int) -> str:
    session = SessionLocal()
    try:
        return session.get(MediaServerEntity, server_id).token
    finally:
        session.close()

def _accepting_connector(monkeypatch):
    connector = MagicMock()
    connector.return_value.get_server_info.return_value = {"friendly_name": "Seeded"}
    monkeypatch.setattr(probe_module, "PlexService", connector)
    monkeypatch.setattr(probe_module, "JellyfinService", connector)
    return connector

def test_a_new_token_replaces_the_stored_one(authenticated_app, monkeypatch):
    server_id = _seed_server()
    _accepting_connector(monkeypatch)

    with TestClient(authenticated_app) as client:
        resp = client.patch(f"/affiche/media-servers/{server_id}/token",
                            json={"token": NEW_TOKEN})

    assert resp.status_code == 200, resp.text
    assert _stored_token(server_id) == NEW_TOKEN

def test_the_response_carries_no_token_at_all(authenticated_app, monkeypatch):
    server_id = _seed_server()
    _accepting_connector(monkeypatch)

    with TestClient(authenticated_app) as client:
        body = client.patch(f"/affiche/media-servers/{server_id}/token",
                            json={"token": NEW_TOKEN}).json()

    assert "token" not in body
    assert NEW_TOKEN not in str(body)
    assert OLD_TOKEN not in str(body)

def test_the_server_is_never_readable_with_its_token(authenticated_app, monkeypatch):
    server_id = _seed_server()
    _accepting_connector(monkeypatch)

    with TestClient(authenticated_app) as client:
        one = client.get(f"/affiche/media-servers/{server_id}").json()
        listing = client.get("/affiche/media-servers/").json()

    assert OLD_TOKEN not in str(one)
    assert OLD_TOKEN not in str(listing)

def test_the_candidate_is_verified_against_the_server_before_it_is_stored(authenticated_app,
                                                                          monkeypatch):
    server_id = _seed_server()
    connector = _accepting_connector(monkeypatch)

    with TestClient(authenticated_app) as client:
        client.patch(f"/affiche/media-servers/{server_id}/token", json={"token": NEW_TOKEN})

    assert connector.call_args.args[1] == NEW_TOKEN

def test_the_cached_connector_is_invalidated(authenticated_app, monkeypatch):
    server_id = _seed_server()
    _accepting_connector(monkeypatch)
    invalidated = []
    internal_event_bus.subscribe("media_server.updated",
                                 lambda media_server_id: invalidated.append(media_server_id))

    with TestClient(authenticated_app) as client:
        client.patch(f"/affiche/media-servers/{server_id}/token", json={"token": NEW_TOKEN})

    assert invalidated == [server_id]

def test_a_token_the_server_rejects_is_not_stored(authenticated_app, monkeypatch):
    from plexapi.exceptions import Unauthorized

    server_id = _seed_server()
    connector = MagicMock()
    connector.return_value.get_server_info.side_effect = Unauthorized("bad token")
    monkeypatch.setattr(probe_module, "PlexService", connector)

    with TestClient(authenticated_app) as client:
        resp = client.patch(f"/affiche/media-servers/{server_id}/token",
                            json={"token": NEW_TOKEN})

    assert resp.status_code == 401
    assert _stored_token(server_id) == OLD_TOKEN

def test_an_unreachable_server_is_a_502_and_changes_nothing(authenticated_app, monkeypatch):
    server_id = _seed_server()
    connector = MagicMock()
    connector.return_value.get_server_info.side_effect = ConnectionError("down")
    monkeypatch.setattr(probe_module, "PlexService", connector)

    with TestClient(authenticated_app) as client:
        resp = client.patch(f"/affiche/media-servers/{server_id}/token",
                            json={"token": NEW_TOKEN})

    assert resp.status_code == 502
    assert _stored_token(server_id) == OLD_TOKEN

def test_a_jellyfin_key_rejected_with_401_is_reported_as_a_bad_key(authenticated_app, monkeypatch):
    import requests

    server_id = _seed_server(type_=MediaServerType.JELLYFIN)
    response = MagicMock(status_code=401)
    connector = MagicMock()
    connector.return_value.get_server_info.side_effect = requests.HTTPError(response=response)
    monkeypatch.setattr(probe_module, "JellyfinService", connector)

    with TestClient(authenticated_app) as client:
        resp = client.patch(f"/affiche/media-servers/{server_id}/token",
                            json={"token": NEW_TOKEN})

    assert resp.status_code == 401
    assert _stored_token(server_id) == OLD_TOKEN

def test_a_blank_token_is_refused_without_touching_the_server(authenticated_app, monkeypatch):
    server_id = _seed_server()
    connector = _accepting_connector(monkeypatch)

    with TestClient(authenticated_app) as client:
        resp = client.patch(f"/affiche/media-servers/{server_id}/token", json={"token": "   "})

    assert resp.status_code == 400
    assert connector.call_count == 0
    assert _stored_token(server_id) == OLD_TOKEN

def test_an_unknown_server_is_a_404(authenticated_app, monkeypatch):
    _accepting_connector(monkeypatch)

    with TestClient(authenticated_app) as client:
        resp = client.patch("/affiche/media-servers/999999/token", json={"token": NEW_TOKEN})

    assert resp.status_code == 404

def test_the_endpoint_is_session_gated():
    with TestClient(main_module.app) as client:
        resp = client.patch("/affiche/media-servers/1/token", json={"token": NEW_TOKEN})

    assert resp.status_code == 401
