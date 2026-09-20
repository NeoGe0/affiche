from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.config.dependencies import get_poster_aggregator
from affiche.external.poster.poster_service import PosterAggregatorService, ProviderPoster
from affiche.external.poster.provider.base_provider import PosterImage
from affiche.external.poster.provider.fanart import FanartClient
from affiche.external.poster.provider.mediux import MediuxClient
from affiche.external.poster.provider.shoko import ShokoClient
from affiche.external.poster.provider.tmdb import TMDBClient
from affiche.external.poster.provider.tvdb import TVDBClient
from affiche.external.poster.provider.tvmaze import TVmazeClient

def _meta(image):
    return (str(image), image.language, image.textless, image.width, image.height)

def _json_session(payload):
    session = MagicMock()
    session.get.return_value.json.return_value = payload
    return session

def test_a_poster_image_still_compares_as_its_url():
    image = PosterImage("http://x/a.jpg", language="EN", width=0)

    assert image == "http://x/a.jpg"
    assert (image.language, image.width) == ("en", None)

def test_tmdb_reads_a_null_or_xx_code_as_textless():
    client = TMDBClient("key")
    client.session = _json_session({"posters": [
        {"file_path": "/a.jpg", "iso_639_1": None, "width": 2000, "height": 3000, "vote_average": 9},
        {"file_path": "/b.jpg", "iso_639_1": "xx", "width": 1000, "height": 1500, "vote_average": 8},
        {"file_path": "/c.jpg", "iso_639_1": "fr", "width": 1400, "height": 2100, "vote_average": 7},
    ]})

    base = TMDBClient.IMAGE_BASE_URL
    assert [_meta(p) for p in client.get_all_posters("movie", tmdb_id=1)] == [
        (f"{base}/a.jpg", None, True, 2000, 3000),
        (f"{base}/b.jpg", None, True, 1000, 1500),
        (f"{base}/c.jpg", "fr", False, 1400, 2100),
    ]

def test_fanart_reads_00_as_textless_and_publishes_no_size():
    client = FanartClient("key")
    client.session = _json_session({"tvposter": [
        {"url": "http://fanart/a.jpg", "lang": "00"},
        {"url": "http://fanart/b.jpg", "lang": "en"},
        {"url": "http://fanart/c.jpg", "lang": ""},
    ]})

    assert [_meta(p) for p in client.get_all_posters("show", tvdb_id=1)] == [
        ("http://fanart/a.jpg", None, True, None, None),
        ("http://fanart/b.jpg", "en", False, None, None),
        ("http://fanart/c.jpg", None, None, None, None),
    ]

def test_tvdb_maps_its_three_letter_codes_and_reads_null_as_textless():
    client = TVDBClient("key")
    client._tvdb = MagicMock()
    client._tvdb.get_series_artworks.return_value = {"artworks": [
        {"image": "http://tvdb/a.jpg", "language": None, "width": 680, "height": 1000, "score": 3},
        {"image": "http://tvdb/b.jpg", "language": "fra", "width": 680, "height": 1000, "score": 2},
        {"image": "http://tvdb/c.jpg", "language": "heb", "width": 680, "height": 1000, "score": 1},
    ]}

    assert [_meta(p) for p in client.get_all_posters("show", tvdb_id=1)] == [
        ("http://tvdb/a.jpg", None, True, 680, 1000),
        ("http://tvdb/b.jpg", "fr", False, 680, 1000),
        ("http://tvdb/c.jpg", "heb", False, 680, 1000),
    ]

def test_mediux_passes_its_language_on_but_never_claims_textless():
    client = MediuxClient(api_key="k", base_url="https://api.mediux.io")
    sets = {"movies_by_id": {"movie_sets": [{"movie_poster": [
        {"id": "a1", "language": {"iso_639_1": "en"}},
        {"id": "b2", "language": None},
    ]}]}}

    with patch.object(client, "_query", return_value=sets):
        posters = client.get_all_posters("movie", tmdb_id=1)

    assert [(p.language, p.textless, p.width) for p in posters] == [("en", None, None),
                                                                     (None, None, None)]

def test_shoko_carries_its_language_and_size():
    client = ShokoClient(api_key="k", base_url="http://shoko:8111")
    payloads = {
        "/api/v3/Tmdb/": [{"IDs": {"ID": 7}}],
        "/api/v3/Series/7/Images": {"Posters": [
            {"UID": "a", "Source": "AniDB", "Width": 600, "Height": 850, "LanguageCode": "ja"},
        ]},
    }

    def _get(path, params=None):
        return next((v for k, v in payloads.items() if path.startswith(k)), None)

    with patch.object(client, "_get", side_effect=_get):
        [poster] = client.get_all_posters("show", tmdb_id=1)

    assert (poster.language, poster.textless, poster.width, poster.height) == ("ja", None, 600, 850)

def test_tvmaze_carries_the_size_and_no_language():
    client = TVmazeClient()
    client._MIN_REQUEST_INTERVAL = 0
    payloads = {
        "/lookup/shows": {"id": 3},
        "/shows/3/images": [{"type": "poster", "resolutions": {
            "original": {"url": "http://maze/a.jpg", "width": 680, "height": 1000}}}],
    }

    def _get(path, params=None):
        return payloads.get(path)

    with patch.object(client, "_get", side_effect=_get):
        [poster] = client.get_all_posters("show", tvdb_id=1)

    assert _meta(poster) == ("http://maze/a.jpg", None, None, 680, 1000)

class _ImageProvider(TMDBClient):
    def __init__(self, posters):
        super().__init__("key")
        self._posters = posters

    def get_all_posters(self, media_type, tmdb_id=None, tvdb_id=None, language=None):
        return self._posters

def test_the_aggregator_copies_the_metadata_onto_each_candidate():
    aggregator = PosterAggregatorService([_ImageProvider([
        PosterImage("http://tmdb/a.jpg", textless=True, width=2000, height=3000),
        "http://tmdb/plain.jpg",
    ])])

    candidates = aggregator.get_all_posters(media_type="movie", tmdb_id=1)

    assert candidates[0] == ProviderPoster("http://tmdb/a.jpg", "tmdb", rank=0, rank_score=1.0,
                                           textless=True, width=2000, height=3000)
    assert (candidates[1].language, candidates[1].textless, candidates[1].width) == (None, None, None)
    assert type(candidates[0].url) is str

def test_the_browse_endpoint_sends_it_to_the_grid(authenticated_app):
    stub = MagicMock()
    stub.get_all_posters.return_value = [
        ProviderPoster("http://tmdb/a.jpg", "tmdb", language="fr", textless=False,
                       width=1400, height=2100),
    ]
    authenticated_app.dependency_overrides[get_poster_aggregator] = lambda: stub
    try:
        with TestClient(authenticated_app) as client:
            resp = client.get("/affiche/service/posters?tmdb_id=550&media_type=movie")
    finally:
        authenticated_app.dependency_overrides.pop(get_poster_aggregator, None)

    [candidate] = resp.json()
    assert {k: candidate[k] for k in ("language", "textless", "width", "height")} == {
        "language": "fr", "textless": False, "width": 1400, "height": 2100,
    }
