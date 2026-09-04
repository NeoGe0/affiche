from unittest.mock import patch

import pytest

from affiche.app.service_configuration.provider_service import EXTERNAL_PROVIDERS
from affiche.config.library_config import DEFAULT_PROVIDER_ORDER
from affiche.external.poster.provider.tvmaze import TVmazeClient

SHOW = {"id": 143, "name": "A Series"}

IMAGES = [
    {"type": "poster", "main": True,
     "resolutions": {"original": {"url": "https://static.tvmaze.com/small.jpg",
                                  "width": 680, "height": 1000}}},
    {"type": "background", "main": False,
     "resolutions": {"original": {"url": "https://static.tvmaze.com/backdrop.jpg",
                                  "width": 1920, "height": 1080}}},
    {"type": "poster", "main": False,
     "resolutions": {"original": {"url": "https://static.tvmaze.com/big.jpg",
                                  "width": 1200, "height": 1800}}},
    {"type": "poster", "main": False,
     "resolutions": {"original": {"url": "https://static.tvmaze.com/tiny.jpg",
                                  "width": 210, "height": 295}}},
]

SEASONS = [
    {"number": 1, "image": {"original": "https://static.tvmaze.com/s1.jpg"}},
    {"number": 2, "image": None},
    {"number": 3, "image": {"original": "https://static.tvmaze.com/s3.jpg"}},
]

def _client() -> TVmazeClient:
    client = TVmazeClient()
    client._MIN_REQUEST_INTERVAL = 0
    return client

def _responder(**by_path):
    def _get(path, params=None):
        for prefix, payload in by_path.items():
            if path.startswith(prefix):
                return payload
        return None
    return _get

def test_tvmaze_is_registered_and_ranked_behind_every_keyed_provider():
    assert EXTERNAL_PROVIDERS.get("tvmaze") is TVmazeClient
    assert TVmazeClient().name == "tvmaze"
    assert DEFAULT_PROVIDER_ORDER[-2:] == ["tvmaze", "shoko"]

def test_tvmaze_needs_no_api_key():
    assert TVmazeClient.requires_api_key is False

def test_posters_are_returned_largest_first():
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/images": IMAGES})):
        posters = client.get_all_posters("show", tvdb_id=81189)

    assert posters == ["https://static.tvmaze.com/big.jpg", "https://static.tvmaze.com/small.jpg"]

def test_non_poster_artwork_and_undersized_images_are_dropped():
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/images": IMAGES})):
        posters = client.get_all_posters("show", tvdb_id=81189)

    assert "https://static.tvmaze.com/backdrop.jpg" not in posters
    assert "https://static.tvmaze.com/tiny.jpg" not in posters

def test_an_image_without_a_declared_width_is_kept():
    images = [{"type": "poster",
               "resolutions": {"original": {"url": "https://static.tvmaze.com/nosize.jpg"}}}]
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/images": images})):
        assert client.get_all_posters("show", tvdb_id=81189) == [
            "https://static.tvmaze.com/nosize.jpg"]

def test_get_show_poster_is_the_first_of_get_all_posters():
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/images": IMAGES})):
        assert client.get_show_poster(tvdb_id=81189) == "https://static.tvmaze.com/big.jpg"

def test_movies_are_not_looked_up_at_all():
    client = _client()
    with patch.object(TVmazeClient, "_get") as get:
        assert client.get_movie_poster(tmdb_id=550, tvdb_id=1) is None
        assert client.get_all_posters("movie", tmdb_id=550, tvdb_id=1) == []
    get.assert_not_called()

def test_a_missing_tvdb_id_costs_no_request():
    client = _client()
    with patch.object(TVmazeClient, "_get") as get:
        assert client.get_all_posters("show", tmdb_id=42) == []
        assert client.get_all_season_posters(1, tmdb_id=42) == []
    get.assert_not_called()

def test_season_poster_is_matched_by_number():
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/seasons": SEASONS})):
        assert client.get_season_poster(3, tvdb_id=81189) == "https://static.tvmaze.com/s3.jpg"

def test_a_season_with_no_artwork_yields_nothing():
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/seasons": SEASONS})):
        assert client.get_all_season_posters(2, tvdb_id=81189) == []

def test_an_unknown_season_number_yields_nothing():
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/seasons": SEASONS})):
        assert client.get_all_season_posters(9, tvdb_id=81189) == []

def test_the_show_id_is_resolved_once_and_reused():
    client = _client()
    calls = []

    def _get(path, params=None):
        calls.append(path)
        return _responder(**{"/lookup": SHOW, "/shows/143/images": IMAGES,
                             "/shows/143/seasons": SEASONS})(path, params)

    with patch.object(TVmazeClient, "_get", side_effect=_get):
        client.get_show_poster(tvdb_id=81189)
        client.get_season_poster(1, tvdb_id=81189)
        client.get_season_poster(3, tvdb_id=81189)

    assert len([p for p in calls if p.startswith("/lookup")]) == 1

def test_a_series_tvmaze_does_not_have_is_cached_as_a_miss():
    client = _client()
    calls = []

    def _get(path, params=None):
        calls.append(path)
        return None

    with patch.object(TVmazeClient, "_get", side_effect=_get):
        assert client.get_show_poster(tvdb_id=999) is None
        assert client.get_season_poster(1, tvdb_id=999) is None

    assert calls == ["/lookup/shows"]

def test_the_lookup_is_keyed_on_the_tvdb_id():
    client = _client()
    with patch.object(TVmazeClient, "_get", return_value=SHOW) as get:
        client._resolve_show_id(81189)

    get.assert_called_once_with("/lookup/shows", params={"thetvdb": 81189})

@pytest.mark.parametrize("payload", [None, {}, [], "nonsense"])
def test_an_unusable_payload_degrades_to_no_posters(payload):
    client = _client()
    with patch.object(TVmazeClient, "_get",
                      side_effect=_responder(**{"/lookup": SHOW, "/shows/143/images": payload})):
        assert client.get_all_posters("show", tvdb_id=81189) == []

def test_a_transport_error_is_swallowed():
    import requests

    client = _client()
    with patch.object(client.session, "get", side_effect=requests.RequestException("boom")):
        assert client.get_all_posters("show", tvdb_id=81189) == []

def test_a_rate_limited_response_yields_no_posters_rather_than_raising():
    import requests
    from unittest.mock import MagicMock

    client = _client()
    response = MagicMock(status_code=429)
    with patch.object(client.session, "get", return_value=response):
        assert client.get_all_posters("show", tvdb_id=81189) == []
    response.raise_for_status.assert_not_called()
    assert requests

def test_consecutive_requests_are_spaced_apart():
    client = TVmazeClient()
    client._MIN_REQUEST_INTERVAL = 0.05

    import time
    started = time.monotonic()
    client._await_rate_limit()
    client._await_rate_limit()
    elapsed = time.monotonic() - started

    assert elapsed >= 0.05
