from unittest.mock import MagicMock, patch

import pytest
import requests

from affiche.app.service_configuration.provider_service import EXTERNAL_PROVIDERS
from affiche.config.library_config import DEFAULT_PROVIDER_ORDER
from affiche.external.poster.provider.base_provider import BaseUrlMode
from affiche.external.poster.provider.shoko import (
    ShokoClient,
    is_shoko_url,
    shoko_download_headers,
)

BASE = "http://192.168.1.50:8111"

SERIES = [{"IDs": {"ID": 77, "AniDB": 1234}, "Name": "An Anime"}]

IMAGES = {
    "Posters": [
        {"UID": "aaa", "Source": "AniDB", "Width": 600, "Height": 850, "LanguageCode": "ja"},
        {"UID": "bbb", "Source": "TMDB", "Width": 2000, "Height": 3000, "LanguageCode": "en"},
        {"UID": "ccc", "Source": "User", "Width": 1400, "Height": 2100, "LanguageCode": None},
        {"UID": "ddd", "Source": "AniDB", "Width": 300, "Height": 450, "LanguageCode": "ja"},
    ],
    "Backdrops": [
        {"UID": "eee", "Source": "AniDB", "Width": 1920, "Height": 1080},
    ],
}

def _client() -> ShokoClient:
    return ShokoClient(api_key="a-key", base_url=BASE)

def _responder(**by_path):
    def _get(path, params=None):
        for prefix, payload in by_path.items():
            if path.startswith(prefix):
                return payload
        return None
    return _get

def _images_responder(images=IMAGES, series=SERIES):
    return _responder(**{"/api/v3/Tmdb": series, "/api/v3/Series/77/Images": images})

def test_shoko_is_registered_and_ranked_last():
    assert EXTERNAL_PROVIDERS.get("shoko") is ShokoClient
    assert ShokoClient().name == "shoko"
    assert DEFAULT_PROVIDER_ORDER[-1] == "shoko"

def test_shoko_needs_both_a_key_and_a_user_supplied_url():
    assert ShokoClient.requires_api_key is True
    assert ShokoClient.base_url_mode is BaseUrlMode.USER

def test_the_api_key_travels_as_the_apikey_header():
    session = requests.Session()
    _client()._configure_session(session)
    assert session.headers["apikey"] == "a-key"

def test_a_trailing_slash_on_the_base_url_is_dropped():
    assert ShokoClient(base_url="http://host:8111/").base_url == "http://host:8111"

def test_posters_are_returned_largest_first():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()):
        posters = client.get_all_posters("show", tmdb_id=1429)

    assert posters == [f"{BASE}/api/v3/Image/ccc", f"{BASE}/api/v3/Image/aaa"]

def test_tmdb_sourced_images_are_excluded():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()):
        posters = client.get_all_posters("show", tmdb_id=1429)

    assert f"{BASE}/api/v3/Image/bbb" not in posters

def test_backdrops_and_undersized_posters_are_dropped():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()):
        posters = client.get_all_posters("show", tmdb_id=1429)

    assert f"{BASE}/api/v3/Image/eee" not in posters
    assert f"{BASE}/api/v3/Image/ddd" not in posters

def test_an_image_without_a_declared_width_is_kept():
    images = {"Posters": [{"UID": "nos", "Source": "AniDB"}]}
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder(images=images)):
        assert client.get_all_posters("show", tmdb_id=1429) == [f"{BASE}/api/v3/Image/nos"]

def test_get_show_poster_is_the_first_of_get_all_posters():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()):
        assert client.get_show_poster(tmdb_id=1429) == f"{BASE}/api/v3/Image/ccc"

def test_movies_resolve_through_the_movie_endpoint():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()) as get:
        client.get_movie_poster(tmdb_id=129)

    assert get.call_args_list[0].args[0] == "/api/v3/Tmdb/Movie/129/Shoko/Series"

def test_shows_resolve_through_the_show_endpoint():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()) as get:
        client.get_show_poster(tmdb_id=1429)

    assert get.call_args_list[0].args[0] == "/api/v3/Tmdb/Show/1429/Shoko/Series"

def test_a_tvdb_only_item_costs_no_request():
    client = _client()
    with patch.object(ShokoClient, "_get") as get:
        assert client.get_all_posters("show", tvdb_id=81189) == []
        assert client.get_show_poster(tvdb_id=81189) is None
    get.assert_not_called()

def test_an_unconfigured_base_url_costs_no_request():
    client = ShokoClient(api_key="k", base_url="")
    with patch.object(ShokoClient, "_get") as get:
        assert client.get_all_posters("show", tmdb_id=1429) == []
    get.assert_not_called()

def test_a_language_preference_keeps_only_that_language():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()):
        assert client.get_all_posters("show", tmdb_id=1429, language="ja") == [
            f"{BASE}/api/v3/Image/aaa"]

def test_no_language_preference_keeps_every_poster():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()):
        assert client.get_all_posters("show", tmdb_id=1429, language=None) == [
            f"{BASE}/api/v3/Image/ccc", f"{BASE}/api/v3/Image/aaa"]

def test_a_language_request_does_not_match_an_untitled_poster():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()):
        assert f"{BASE}/api/v3/Image/ccc" not in client.get_all_posters(
            "show", tmdb_id=1429, language="fr")

def test_season_posters_are_always_empty_and_cost_no_request():
    client = _client()
    with patch.object(ShokoClient, "_get") as get:
        assert client.get_all_season_posters(1, tmdb_id=1429) == []
        assert client.get_season_poster(1, tmdb_id=1429) is None
    get.assert_not_called()

def test_the_series_id_is_resolved_once_and_reused():
    client = _client()
    calls = []

    def _get(path, params=None):
        calls.append(path)
        return _images_responder()(path, params)

    with patch.object(ShokoClient, "_get", side_effect=_get):
        client.get_show_poster(tmdb_id=1429)
        client.get_show_poster(tmdb_id=1429)

    assert len([p for p in calls if p.startswith("/api/v3/Tmdb")]) == 1

def test_an_anime_not_in_the_collection_is_cached_as_a_miss():
    client = _client()
    calls = []

    def _get(path, params=None):
        calls.append(path)
        return None

    with patch.object(ShokoClient, "_get", side_effect=_get):
        assert client.get_show_poster(tmdb_id=999) is None
        assert client.get_show_poster(tmdb_id=999) is None

    assert calls == ["/api/v3/Tmdb/Show/999/Shoko/Series"]

def test_movies_and_shows_are_cached_separately():
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder()) as get:
        client.get_show_poster(tmdb_id=42)
        client.get_movie_poster(tmdb_id=42)

    resolutions = [c.args[0] for c in get.call_args_list if c.args[0].startswith("/api/v3/Tmdb")]
    assert resolutions == ["/api/v3/Tmdb/Show/42/Shoko/Series",
                           "/api/v3/Tmdb/Movie/42/Shoko/Series"]

@pytest.mark.parametrize("payload", [None, {}, [], "nonsense", {"Posters": None}])
def test_an_unusable_payload_degrades_to_no_posters(payload):
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder(images=payload)):
        assert client.get_all_posters("show", tmdb_id=1429) == []

@pytest.mark.parametrize("payload", [None, [], "nonsense", [{"IDs": {}}], [{"IDs": {"ID": "x"}}]])
def test_an_unusable_series_payload_degrades_to_no_posters(payload):
    client = _client()
    with patch.object(ShokoClient, "_get", side_effect=_images_responder(series=payload)):
        assert client.get_all_posters("show", tmdb_id=1429) == []

def test_a_transport_error_is_swallowed():
    client = _client()
    with patch.object(client.session, "get", side_effect=requests.RequestException("boom")):
        assert client.get_all_posters("show", tmdb_id=1429) == []

@pytest.mark.parametrize("status", [401, 403])
def test_a_revoked_key_yields_no_posters_rather_than_raising(status):
    client = _client()
    response = MagicMock(status_code=status)
    with patch.object(client.session, "get", return_value=response):
        assert client.get_all_posters("show", tmdb_id=1429) == []
    response.raise_for_status.assert_not_called()

def test_is_shoko_url_matches_only_the_exact_origin():
    assert is_shoko_url(f"{BASE}/api/v3/Image/aaa", BASE)
    assert not is_shoko_url("http://192.168.1.50:9000/api/v3/Image/aaa", BASE)
    assert not is_shoko_url("http://192.168.1.51:8111/api/v3/Image/aaa", BASE)
    assert not is_shoko_url("https://192.168.1.50:8111/api/v3/Image/aaa", BASE)
    assert not is_shoko_url("http://evil.example/192.168.1.50:8111", BASE)

def test_is_shoko_url_is_closed_when_nothing_is_configured():
    assert not is_shoko_url(f"{BASE}/api/v3/Image/aaa", None)
    assert not is_shoko_url(f"{BASE}/api/v3/Image/aaa", "")
    assert not is_shoko_url("", BASE)

def test_download_headers_carry_the_key_only_for_the_configured_origin():
    assert shoko_download_headers(f"{BASE}/api/v3/Image/aaa", BASE, "a-key")["apikey"] == "a-key"
    assert shoko_download_headers("http://elsewhere:8111/x", BASE, "a-key") == {}
    assert shoko_download_headers(f"{BASE}/api/v3/Image/aaa", BASE, None) == {}
