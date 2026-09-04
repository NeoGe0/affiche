import logging
from unittest.mock import patch

from affiche.app.service_configuration.provider_service import EXTERNAL_PROVIDERS
from affiche.config.library_config import DEFAULT_PROVIDER_ORDER
from affiche.external.poster.provider.mediux import (
    MediuxClient, is_mediux_url, mediux_download_headers, _normalize_token,
)

def test_token_normalization_strips_bearer_and_whitespace():
    assert _normalize_token("Bearer abc123") == "abc123"
    assert _normalize_token("bearer abc123") == "abc123"
    assert _normalize_token("  abc123  ") == "abc123"
    assert _normalize_token(None) == ""
    client = MediuxClient(api_key="Bearer abc123")
    assert client.api_key == "abc123"
    assert client.session.headers["Authorization"] == "Bearer abc123"

class _FakeSession:

    def __init__(self, payload):
        self._payload = payload
        self.headers = {}

    def post(self, *_args, **_kwargs):
        return _FakeResponse(self._payload)

class _FakeResponse:

    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._payload

def test_provider_registered_and_in_default_order():
    assert EXTERNAL_PROVIDERS.get("mediux") is MediuxClient
    assert MediuxClient(api_key="x").name == "mediux"
    assert DEFAULT_PROVIDER_ORDER.index("mediux") > DEFAULT_PROVIDER_ORDER.index("fanart")

def test_is_mediux_url():
    assert is_mediux_url("https://images.mediux.io/assets/abc?v=1")
    assert is_mediux_url("https://mediux.io/assets/abc")
    assert not is_mediux_url("https://image.tmdb.org/t/p/original/x.jpg")
    assert not is_mediux_url("")

def test_mediux_download_headers():
    assert mediux_download_headers("https://images.mediux.io/assets/a", "tok") == {
        "Authorization": "Bearer tok", "Accept": "image/*",
    }
    assert mediux_download_headers("https://images.mediux.io/assets/a", None) == {}
    assert mediux_download_headers("https://image.tmdb.org/x.jpg", "tok") == {}

def test_format_modified_and_asset_url():
    assert MediuxClient._format_modified("2024-01-15T10:30:45") == "20240115103045"
    assert MediuxClient._format_modified("2024-01-15T10:30:45Z") == "20240115103045"
    assert MediuxClient._format_modified(None) is None
    assert MediuxClient._format_modified("garbage") is None

    c = MediuxClient(api_key="x", base_url="https://images.mediux.io")
    assert c._asset_url({"id": "a1", "modified_on": "2024-01-15T10:30:45"}) == \
        "https://images.mediux.io/assets/a1?v=20240115103045"
    assert c._asset_url({"id": "a1"}) == "https://images.mediux.io/assets/a1"
    assert c._asset_url({}) is None

_SHOW_DATA = {"shows_by_id": {"id": "100", "show_sets": [
    {"popularity": 5, "popularity_global": 10,
     "show_poster": [{"id": "lowpop", "modified_on": "2024-01-01T00:00:00",
                      "language": {"iso_639_1": "en"}}],
     "season_posters": [{"id": "s1en", "modified_on": "2024-01-01T00:00:00",
                         "language": {"iso_639_1": "en"}, "season": {"season_number": 1}}]},
    {"popularity": 9, "popularity_global": 99,
     "show_poster": [{"id": "hipop", "modified_on": "2024-02-02T12:00:00",
                      "language": {"iso_639_1": "fr"}}],
     "season_posters": [{"id": "s1fr", "modified_on": "2024-01-01T00:00:00",
                         "language": {"iso_639_1": "fr"}, "season": {"season_number": 1}},
                        {"id": "s2en", "modified_on": "2024-01-01T00:00:00",
                         "language": {"iso_639_1": "en"}, "season": {"season_number": 2}}]},
]}}

def test_posters_ordered_by_set_popularity():
    c = MediuxClient(api_key="x")
    with patch.object(MediuxClient, "_query", return_value=_SHOW_DATA):
        urls = c.get_all_posters("show", tmdb_id=100)
        assert "hipop" in urls[0] and "lowpop" in urls[1]
        assert c.get_show_poster(tmdb_id=100) == urls[0]

def test_language_match_floated_first():
    c = MediuxClient(api_key="x")
    with patch.object(MediuxClient, "_query", return_value=_SHOW_DATA):
        urls = c.get_all_posters("show", tmdb_id=100, language="en")
        assert "lowpop" in urls[0]

def test_season_posters_collected_and_language_preferred():
    c = MediuxClient(api_key="x")
    with patch.object(MediuxClient, "_query", return_value=_SHOW_DATA):
        s1 = c.get_all_season_posters(1, tmdb_id=100)
        assert any("s1en" in u for u in s1) and any("s1fr" in u for u in s1)
        assert "s1fr" in c.get_all_season_posters(1, tmdb_id=100, language="fr")[0]
        s2 = c.get_all_season_posters(2, tmdb_id=100)
        assert len(s2) == 1 and "s2en" in s2[0]

def test_tvdb_id_resolved_to_tmdb():
    c = MediuxClient(api_key="x")
    calls = []

    def fake_query(self, query, variables):
        calls.append(variables)
        return {"shows": [{"id": "555"}]} if "findShowByTvdb" in query else _SHOW_DATA

    with patch.object(MediuxClient, "_query", fake_query):
        assert c.get_all_posters("show", tvdb_id=81189)
        assert calls[0] == {"tvdb_id": "81189"}
        assert calls[1] == {"tmdb_id": "555"}

def test_missing_item_and_query_failure_return_empty():
    c = MediuxClient(api_key="x")
    with patch.object(MediuxClient, "_query", return_value={"shows_by_id": None}):
        assert c.get_all_posters("show", tmdb_id=1) == []
    with patch.object(MediuxClient, "_query", return_value=None):
        assert c.get_movie_poster(tmdb_id=1) is None
        assert c.get_all_posters("show", tvdb_id=1) == []

_COLLECTION_DATA = {"collections_by_id": {"id": "10", "collection_sets": [
    {"popularity": 13, "popularity_global": 372,
     "collection_poster": [{"id": "lowpop", "modified_on": "2024-01-15T16:59:55.000Z",
                            "language": {"iso_639_1": "en"}}]},
    {"popularity": 34, "popularity_global": 802,
     "collection_poster": [{"id": "hipop", "modified_on": "2024-01-24T15:30:48.000Z",
                            "language": {"iso_639_1": "fr"}}]},
    {"popularity": 2, "popularity_global": 5, "collection_poster": []},
]}}

def test_collections_are_declared_supported():
    assert MediuxClient.supports_collections is True

def test_collection_posters_ordered_by_set_popularity():
    c = MediuxClient(api_key="x", base_url="https://images.mediux.io")
    with patch.object(MediuxClient, "_query", return_value=_COLLECTION_DATA):
        urls = c.get_all_collection_posters(10)
        assert len(urls) == 2
        assert "hipop" in urls[0] and "lowpop" in urls[1]

def test_collection_posters_prefer_the_requested_language():
    c = MediuxClient(api_key="x")
    with patch.object(MediuxClient, "_query", return_value=_COLLECTION_DATA):
        assert "lowpop" in c.get_all_collection_posters(10, language="en")[0]

def test_the_collection_is_queried_by_its_tmdb_id():
    c = MediuxClient(api_key="x")
    seen = []

    def fake_query(self, query, variables):
        seen.append((query, variables))
        return _COLLECTION_DATA

    with patch.object(MediuxClient, "_query", fake_query):
        c.get_all_collection_posters(10)

    assert "collections_by_id" in seen[0][0]
    assert seen[0][1] == {"collection_id": "10"}

def test_a_collection_id_is_resolved_from_a_member():
    c = MediuxClient(api_key="x")
    data = {"movies_by_id": {"collection_id": {"id": "10"}}}
    with patch.object(MediuxClient, "_query", return_value=data):
        assert c.find_collection_id(11) == 10

def test_a_movie_in_no_collection_resolves_to_nothing():
    c = MediuxClient(api_key="x")
    for data in ({"movies_by_id": {"collection_id": None}}, {"movies_by_id": None}, None):
        with patch.object(MediuxClient, "_query", return_value=data):
            assert c.find_collection_id(11) is None

def test_a_non_numeric_collection_id_is_refused():
    c = MediuxClient(api_key="x")
    with patch.object(MediuxClient, "_query", return_value={
            "movies_by_id": {"collection_id": {"id": "not-a-number"}}}):
        assert c.find_collection_id(11) is None

def test_an_unknown_collection_or_a_failed_query_returns_empty():
    c = MediuxClient(api_key="x")
    with patch.object(MediuxClient, "_query", return_value={"collections_by_id": None}):
        assert c.get_all_collection_posters(999999) == []
    with patch.object(MediuxClient, "_query", return_value=None):
        assert c.get_all_collection_posters(10) == []

def test_an_uncatalogued_entry_is_absence_not_an_error(caplog):
    c = MediuxClient(api_key="x")
    forbidden = {
        "data": {"collections_by_id": None},
        "errors": [{"message": "You don't have permission to access this.",
                    "extensions": {"code": "FORBIDDEN"}, "path": ["collections_by_id"]}],
    }
    c.session = _FakeSession(forbidden)
    with caplog.at_level(logging.ERROR, logger="affiche.external.poster.provider.mediux"):
        assert c.get_all_collection_posters(99999999) == []
    assert caplog.records == []

def test_a_real_graphql_error_is_still_reported(caplog):
    c = MediuxClient(api_key="x")
    broken = {"data": None, "errors": [{"message": "Cannot query field",
                                        "extensions": {"code": "GRAPHQL_VALIDATION_EXCEPTION"}}]}
    c.session = _FakeSession(broken)
    with caplog.at_level(logging.ERROR, logger="affiche.external.poster.provider.mediux"):
        assert c.get_all_collection_posters(10) == []
    assert any("returned errors" in r.message for r in caplog.records)
