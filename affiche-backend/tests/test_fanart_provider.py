from unittest.mock import MagicMock

import requests

from affiche.external.poster.provider.fanart import FanartClient

def _client() -> FanartClient:
    client = FanartClient("key")
    client.session = MagicMock()
    return client

def test_all_season_posters_no_tvdb_id_returns_empty_without_request():
    client = _client()
    assert client.get_all_season_posters(1, tvdb_id=None) == []
    client.session.get.assert_not_called()

def test_all_posters_missing_ids_return_empty_without_request():
    client = _client()
    assert client.get_all_posters("show", tvdb_id=None) == []
    assert client.get_all_posters("movie", tmdb_id=None) == []
    client.session.get.assert_not_called()

def test_all_season_posters_is_fail_soft_on_error():
    client = _client()
    client.session.get.side_effect = requests.RequestException("fanart down")
    assert client.get_all_season_posters(1, tvdb_id=123) == []
