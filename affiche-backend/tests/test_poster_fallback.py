from unittest.mock import MagicMock

import pytest

from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.service.poster_resolver import (
    PosterResolver,
    ServerPosterSettings,
)
from affiche.config.language_config import TEXTLESS
from affiche.external.poster.poster_service import ProviderPoster

def _hit(url: str, provider: str = "tmdb") -> ProviderPoster:
    return ProviderPoster(url, provider)

LOCAL_COPY = "/filestore/1/42.jpg"
SERVER_URL = "http://plex.local/library/metadata/9/thumb"

def _resolver(aggregator=None, file_store=None) -> PosterResolver:
    return PosterResolver(
        poster_aggregator=aggregator or _no_provider_posters(),
        file_store=file_store or _file_store(has_local_copy=False))

def _no_provider_posters() -> MagicMock:
    aggregator = MagicMock()
    aggregator.find_best_poster.return_value = None
    aggregator.find_best_season_poster.return_value = None
    return aggregator

def _file_store(has_local_copy: bool) -> MagicMock:
    store = MagicMock()
    store.exists.return_value = has_local_copy
    store.path.return_value = LOCAL_COPY
    return store

def _item(**overrides) -> LibraryItem:
    fields = dict(id=42, library_id=1, external_id="x", title="T", type="movie",
                  tmdb_id=7, tvdb_id=None, poster_url=SERVER_URL, processed=False,
                  poster_hash=None)
    fields.update(overrides)
    return LibraryItem(**fields)

def _season(**overrides) -> LibrarySeason:
    fields = dict(id=9, show_id=42, library_id=1, external_id="s", season_number=1,
                  title="Season 1", poster_url=SERVER_URL, processed=False, poster_hash=None)
    fields.update(overrides)
    return LibrarySeason(**fields)

def _settings(fallback=False, skip_style=False, languages=None) -> ServerPosterSettings:
    return ServerPosterSettings(language_order=languages or [TEXTLESS, "en"],
                                fallback_to_server_poster=fallback,
                                skip_style_when_not_textless=skip_style)

def test_no_fallback_when_the_option_is_off():
    assert _resolver().resolve_item_poster(_item(), "movie", ["tmdb"], _settings(fallback=False)) is None

def test_fallback_prefers_the_local_copy_over_a_network_fetch():
    store = _file_store(has_local_copy=True)

    poster = _resolver(file_store=store).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(fallback=True))

    assert poster.source == LOCAL_COPY
    store.exists.assert_called_once_with(1, 42, season_number=None)

def test_fallback_uses_the_poster_url_when_there_is_no_local_copy():
    poster = _resolver(file_store=_file_store(has_local_copy=False)).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(fallback=True))

    assert poster.source == SERVER_URL

def test_a_fallback_poster_is_always_styled():
    poster = _resolver(file_store=_file_store(has_local_copy=True)).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(fallback=True, skip_style=True))

    assert poster.styled is True

def test_fallback_refuses_a_poster_affiche_itself_uploaded():
    store = _file_store(has_local_copy=True)

    assert _resolver(file_store=store).resolve_item_poster(
        _item(poster_hash="abc123"), "movie", ["tmdb"], _settings(fallback=True)) is None
    store.exists.assert_not_called()

def test_fallback_of_a_processed_item_ignores_the_local_copy():
    poster = _resolver(file_store=_file_store(has_local_copy=True)).resolve_item_poster(
        _item(processed=True), "movie", ["tmdb"], _settings(fallback=True))

    assert poster.source == SERVER_URL

def test_fallback_is_none_when_the_server_has_no_poster_either():
    assert _resolver().resolve_item_poster(
        _item(poster_url=None), "movie", ["tmdb"], _settings(fallback=True)) is None

def test_fallback_runs_only_after_every_language_was_tried():
    aggregator = _no_provider_posters()

    _resolver(aggregator, _file_store(has_local_copy=True)).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(fallback=True, languages=[TEXTLESS, "en", "fr"]))

    assert aggregator.find_best_poster.call_count == 3

def test_a_provider_poster_still_wins_over_the_server_one():
    aggregator = MagicMock()
    aggregator.find_best_poster.return_value = _hit("http://tmdb/poster.jpg")

    poster = _resolver(aggregator, _file_store(has_local_copy=True)).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(fallback=True))

    assert poster.source == "http://tmdb/poster.jpg"

def test_seasons_fall_back_to_their_own_server_poster():
    store = _file_store(has_local_copy=True)

    poster = _resolver(file_store=store).resolve_season_poster(
        _item(type="show"), _season(), ["tmdb"], _settings(fallback=True))

    assert poster.source == LOCAL_COPY
    store.exists.assert_called_once_with(1, 42, season_number=1)

def test_a_season_poster_affiche_uploaded_is_refused_too():
    assert _resolver(file_store=_file_store(has_local_copy=True)).resolve_season_poster(
        _item(type="show"), _season(poster_hash="abc123"), ["tmdb"],
        _settings(fallback=True)) is None

@pytest.mark.parametrize("language, skip_style, expected_styled", [
    (TEXTLESS, True, True),
    (TEXTLESS, False, True),
    ("en", True, False),
    ("en", False, True),
])
def test_styling_depends_on_the_language_the_poster_came_from(language, skip_style, expected_styled):
    aggregator = MagicMock()
    aggregator.find_best_poster.return_value = _hit("http://poster.jpg")

    poster = _resolver(aggregator).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(skip_style=skip_style, languages=[language]))

    assert poster.styled is expected_styled

def test_a_textless_hit_is_styled_even_when_a_later_language_would_not_be():
    aggregator = MagicMock()
    aggregator.find_best_poster.return_value = _hit("http://textless.jpg")

    poster = _resolver(aggregator).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings(skip_style=True, languages=[TEXTLESS, "en"]))

    assert poster.styled is True

def test_season_styling_follows_the_same_rule():
    aggregator = MagicMock()
    aggregator.find_best_season_poster.side_effect = [None, _hit("http://s1-en.jpg")]

    poster = _resolver(aggregator).resolve_season_poster(
        _item(type="show"), _season(), ["tmdb"],
        _settings(skip_style=True, languages=[TEXTLESS, "en"]))

    assert poster.source == "http://s1-en.jpg"
    assert poster.styled is False
