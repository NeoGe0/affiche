from unittest.mock import MagicMock

import pytest
import requests
from fastapi.testclient import TestClient
from plexapi.exceptions import Unauthorized

from affiche.app.mediaserver.model.media_server import MediaServerType
from affiche.app.mediaserver.service import media_server_probe_service as probe_module
from affiche.app.mediaserver.service.media_server_probe_service import MediaServerProbeService
from affiche.app.service_configuration.exceptions import (
    MediaServerCredentialsRejectedError,
    MediaServerUnreachableError,
)

PLEX_TEST = "/affiche/media-servers/plex/test"
JELLYFIN_TEST = "/affiche/media-servers/jellyfin/test"

class _RemoteLibrary:

    def __init__(self, id="1", name="Movies", agent="tv.plex.agents.movie", uuid="u1"):
        self.id, self.name, self.type, self.item_count = id, name, "movie", 12
        self.language = "en"
        self.created_at = self.updated_at = None
        if agent is not None:
            self.agent = agent
        if uuid is not None:
            self.uuid = uuid

def _connector(monkeypatch, name="PlexService", *, libraries=None, fails_with=None):
    connector = MagicMock()
    if fails_with is not None:
        connector.return_value.get_server_info.side_effect = fails_with
    else:
        connector.return_value.get_server_info.return_value = {"friendly_name": "Living Room"}
        connector.return_value.get_libraries.return_value = libraries or []
    monkeypatch.setattr(probe_module, name, connector)
    return connector

@pytest.fixture
def client(authenticated_app):
    return TestClient(authenticated_app)

def test_a_probe_reports_the_name_and_maps_the_libraries(monkeypatch):
    _connector(monkeypatch, libraries=[_RemoteLibrary(), _RemoteLibrary(id="2", name="Shows")])

    probe = MediaServerProbeService().probe(MediaServerType.PLEX, "http://plex:32400", "tok")

    assert probe.name == "Living Room"
    assert [library.name for library in probe.libraries] == ["Movies", "Shows"]
    assert probe.libraries[0].agent == "tv.plex.agents.movie"

def test_a_jellyfin_library_has_no_agent_or_uuid(monkeypatch):
    _connector(monkeypatch, "JellyfinService",
               libraries=[_RemoteLibrary(agent=None, uuid=None)])

    probe = MediaServerProbeService().probe(MediaServerType.JELLYFIN, "http://jf:8096", "key")

    assert probe.libraries[0].agent is None
    assert probe.libraries[0].uuid is None

def test_the_credentials_under_test_are_the_ones_used(monkeypatch):
    connector = _connector(monkeypatch, libraries=[])

    MediaServerProbeService().probe(MediaServerType.PLEX, "http://plex:32400", "candidate")

    assert connector.call_args.args == ("http://plex:32400", "candidate")

def test_plex_refusing_the_token_is_a_rejection_not_an_outage(monkeypatch):
    _connector(monkeypatch, fails_with=Unauthorized("nope"))

    with pytest.raises(MediaServerCredentialsRejectedError) as raised:
        MediaServerProbeService().probe(MediaServerType.PLEX, "http://plex:32400", "bad")

    assert str(raised.value) == "Plex rejected that token"

@pytest.mark.parametrize("status", [401, 403])
def test_jellyfin_refusing_the_key_is_read_off_the_status(monkeypatch, status):
    _connector(monkeypatch, "JellyfinService",
               fails_with=requests.HTTPError(response=MagicMock(status_code=status)))

    with pytest.raises(MediaServerCredentialsRejectedError) as raised:
        MediaServerProbeService().probe(MediaServerType.JELLYFIN, "http://jf:8096", "bad")

    assert str(raised.value) == "Jellyfin rejected that API key"

@pytest.mark.parametrize("failure", [
    ConnectionError("refused"),
    requests.HTTPError(response=MagicMock(status_code=500)),
    requests.HTTPError(response=None),
    ValueError("something else entirely"),
])
def test_anything_that_is_not_a_refusal_is_an_outage(monkeypatch, failure):
    _connector(monkeypatch, fails_with=failure)

    with pytest.raises(MediaServerUnreachableError) as raised:
        MediaServerProbeService().probe(MediaServerType.PLEX, "http://plex:32400", "tok")

    assert str(raised.value) == "Failed to connect to Plex"

def test_the_upstream_error_text_never_reaches_the_message(monkeypatch):
    _connector(monkeypatch, fails_with=ConnectionError("failed for http://plex:32400?X-Token=sec"))

    with pytest.raises(MediaServerUnreachableError) as raised:
        MediaServerProbeService().probe(MediaServerType.PLEX, "http://plex:32400", "sec")

    assert "sec" not in str(raised.value)
    assert str(raised.value) == "Failed to connect to Plex"

def test_verifying_a_token_does_not_enumerate_libraries(monkeypatch):
    connector = _connector(monkeypatch, "JellyfinService", libraries=[_RemoteLibrary()])
    server = MagicMock(type=MediaServerType.JELLYFIN, url="http://jf:8096")

    MediaServerProbeService().verify_token(server, "new-key")

    connector.return_value.get_server_info.assert_called_once()
    connector.return_value.get_libraries.assert_not_called()

def test_a_successful_test_returns_the_server_and_its_libraries(client, monkeypatch):
    _connector(monkeypatch, libraries=[_RemoteLibrary()])

    response = client.post(PLEX_TEST, json={"url": "http://plex:32400", "token": "tok"})

    assert response.status_code == 200
    assert response.json()["name"] == "Living Room"
    assert response.json()["libraries"][0]["name"] == "Movies"

def test_a_rejected_credential_is_a_401_that_names_it(client, monkeypatch):
    _connector(monkeypatch, "JellyfinService",
               fails_with=requests.HTTPError(response=MagicMock(status_code=401)))

    response = client.post(JELLYFIN_TEST, json={"url": "http://jf:8096", "api_key": "bad"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Jellyfin rejected that API key"

def test_an_unreachable_server_is_a_502(client, monkeypatch):
    _connector(monkeypatch, fails_with=ConnectionError("down"))

    response = client.post(PLEX_TEST, json={"url": "http://plex:32400", "token": "tok"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to connect to Plex"
