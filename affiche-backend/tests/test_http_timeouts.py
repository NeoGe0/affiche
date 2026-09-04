from unittest.mock import MagicMock

import affiche.external.jellyfin.service.jellyfin_service as jellyfin_mod
import affiche.external.plex.service.plex_service as plex_mod
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService
from affiche.external.plex.service.plex_service import PlexService
from affiche.external.poster.provider.tmdb import TMDBClient
from affiche.external.poster.provider.fanart import FanartClient
from affiche.config.http_config import HTTP_TIMEOUT, HTTP_TIMEOUT_SECONDS

def _mock_requests():
    m = MagicMock()
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {}
    m.get.return_value = resp
    m.post.return_value = resp
    m.delete.return_value = resp
    return m

def test_jellyfin_get_post_delete_pass_timeout(monkeypatch):
    m = _mock_requests()
    monkeypatch.setattr(jellyfin_mod, "requests", m)
    svc = JellyfinService("http://jf", "key")

    svc._get("/items")
    svc._post("/items", data=b"x")
    svc._delete("/items/1")

    assert m.get.call_args.kwargs.get("timeout") == HTTP_TIMEOUT
    assert m.post.call_args.kwargs.get("timeout") == HTTP_TIMEOUT
    assert m.delete.call_args.kwargs.get("timeout") == HTTP_TIMEOUT

def test_tmdb_fetch_passes_timeout():
    client = TMDBClient("key")
    client.session = MagicMock()
    resp = client.session.get.return_value
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"posters": []}

    client._fetch_all_posters(603, "movie")

    assert client.session.get.call_args.kwargs.get("timeout") == HTTP_TIMEOUT

def test_fanart_fetch_passes_timeout():
    client = FanartClient("key")
    client.session = MagicMock()
    resp = client.session.get.return_value
    resp.raise_for_status.return_value = None
    resp.json.return_value = {}

    client._fetch_movie_posters(550)

    assert client.session.get.call_args.kwargs.get("timeout") == HTTP_TIMEOUT

def test_plex_server_constructed_with_timeout(monkeypatch):
    spy = MagicMock()
    monkeypatch.setattr(plex_mod, "PlexServer", spy)
    svc = PlexService("http://plex:32400", "token")

    _ = svc.plex

    assert spy.call_args.kwargs.get("timeout") == HTTP_TIMEOUT_SECONDS
