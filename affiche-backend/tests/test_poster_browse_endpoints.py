from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401  (initialises routers/DI before the imports below)
from affiche.config.dependencies import get_poster_aggregator
from affiche.external.poster.poster_service import ProviderPoster

@pytest.fixture
def aggregator(authenticated_app):
    stub = MagicMock()
    authenticated_app.dependency_overrides[get_poster_aggregator] = lambda: stub
    yield stub
    authenticated_app.dependency_overrides.pop(get_poster_aggregator, None)

def test_the_item_grid_carries_the_provider_of_each_poster(authenticated_app, aggregator):
    aggregator.get_all_posters.return_value = [
        ProviderPoster("http://tmdb/a.jpg", "tmdb"),
        ProviderPoster("http://mediux/b.jpg", "mediux"),
    ]

    with TestClient(authenticated_app) as client:
        resp = client.get("/affiche/service/posters?tmdb_id=550&media_type=movie")

    assert resp.status_code == 200
    assert [(p["url"], p["provider"]) for p in resp.json()] == [
        ("http://tmdb/a.jpg", "tmdb"),
        ("http://mediux/b.jpg", "mediux"),
    ]

def test_the_season_grid_carries_it_too(authenticated_app, aggregator):
    aggregator.get_all_season_posters.return_value = [ProviderPoster("http://tvdb/s1.jpg", "tvdb")]

    with TestClient(authenticated_app) as client:
        resp = client.get("/affiche/service/posters/season?season_number=1&tvdb_id=81189")

    assert [(p["url"], p["provider"]) for p in resp.json()] == [("http://tvdb/s1.jpg", "tvdb")]

def test_the_collection_grid_carries_it_too(authenticated_app, aggregator):
    aggregator.get_all_collection_posters.return_value = [
        ProviderPoster("http://tmdb/bond.jpg", "tmdb")]

    with TestClient(authenticated_app) as client:
        resp = client.get("/affiche/service/collection-posters?collection_id=645")

    assert [(p["url"], p["provider"]) for p in resp.json()] == [("http://tmdb/bond.jpg", "tmdb")]

def test_a_title_search_carries_it_too(authenticated_app, aggregator):
    aggregator.search_by_title.return_value = MagicMock(tmdb_id=550, tvdb_id=None)
    aggregator.get_all_posters.return_value = [ProviderPoster("http://tmdb/fc.jpg", "tmdb")]

    with TestClient(authenticated_app) as client:
        resp = client.get("/affiche/service/posters/search?name=Fight+Club&media_type=movie")

    assert [(p["url"], p["provider"]) for p in resp.json()] == [("http://tmdb/fc.jpg", "tmdb")]
