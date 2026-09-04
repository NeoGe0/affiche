from unittest.mock import MagicMock

from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.service.poster_resolver import (
    PosterResolver,
    ServerPosterSettings,
)
from affiche.config.language_config import (
    DEFAULT_LANGUAGE_ORDER,
    TEXTLESS,
    normalize_language_order,
)
from affiche.external.poster.poster_service import ProviderPoster

def _hit(url: str, provider: str = "tmdb") -> ProviderPoster:
    return ProviderPoster(url, provider)

def _resolver(aggregator) -> PosterResolver:
    return PosterResolver(poster_aggregator=aggregator, file_store=None)

def _settings(language_order) -> ServerPosterSettings:
    return ServerPosterSettings(language_order=language_order,
                                fallback_to_server_poster=False,
                                skip_style_when_not_textless=False)

def test_default_order_is_textless_then_english_then_french():
    assert DEFAULT_LANGUAGE_ORDER == [TEXTLESS, "en", "fr"]

def test_unknown_codes_are_dropped_and_priority_is_preserved():
    assert normalize_language_order(["fr", "klingon", "en"]) == ["fr", "en"]

def test_duplicates_keep_only_their_first_position():
    assert normalize_language_order(["en", "fr", "en"]) == ["en", "fr"]

def test_codes_are_case_insensitive_and_trimmed():
    assert normalize_language_order([" FR ", "EN"]) == ["fr", "en"]

def test_an_emptied_order_falls_back_to_textless_only():
    assert normalize_language_order([]) == [TEXTLESS]
    assert normalize_language_order(None) == [TEXTLESS]
    assert normalize_language_order(["nonsense"]) == [TEXTLESS]

def test_textless_is_a_valid_entry_anywhere_in_the_order():
    assert normalize_language_order(["fr", TEXTLESS]) == ["fr", TEXTLESS]

def _item() -> LibraryItem:
    return LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie",
                       tmdb_id=42, tvdb_id=None)

def _season(number: int = 1):
    from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
    return LibrarySeason(id=7, show_id=1, library_id=1, external_id="s", season_number=number,
                         title="Season %d" % number)

def test_item_poster_falls_back_to_the_next_language():
    aggregator = MagicMock()
    aggregator.find_best_poster.side_effect = [None, None, _hit("http://fr.jpg", "tvdb")]

    poster = _resolver(aggregator).resolve_item_poster(
        _item(), "movie", ["tmdb", "tvdb"], _settings([TEXTLESS, "en", "fr"]))

    assert poster.source == "http://fr.jpg"
    assert [c.kwargs["language"] for c in aggregator.find_best_poster.call_args_list] == [None, "en", "fr"]

def test_item_poster_stops_at_the_first_language_that_has_one():
    aggregator = MagicMock()
    aggregator.find_best_poster.side_effect = [_hit("http://textless.jpg"), _hit("http://en.jpg")]

    poster = _resolver(aggregator).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings([TEXTLESS, "en"]))

    assert poster.source == "http://textless.jpg"
    assert aggregator.find_best_poster.call_count == 1

def test_item_poster_is_none_when_no_language_yields_one():
    aggregator = MagicMock()
    aggregator.find_best_poster.return_value = None

    assert _resolver(aggregator).resolve_item_poster(
        _item(), "movie", ["tmdb"], _settings([TEXTLESS, "en", "fr"])) is None
    assert aggregator.find_best_poster.call_count == 3

def test_the_whole_provider_order_is_tried_per_language():
    aggregator = MagicMock()
    aggregator.find_best_poster.side_effect = [None, _hit("http://en.jpg")]

    _resolver(aggregator).resolve_item_poster(_item(), "movie", ["tmdb", "tvdb"],
                                              _settings([TEXTLESS, "en"]))

    for call in aggregator.find_best_poster.call_args_list:
        assert call.kwargs["provider_order"] == ["tmdb", "tvdb"]

def test_season_poster_follows_the_same_order():
    aggregator = MagicMock()
    aggregator.find_best_season_poster.side_effect = [None, _hit("http://s1-en.jpg")]

    poster = _resolver(aggregator).resolve_season_poster(
        _item(), _season(1), ["tmdb"], _settings([TEXTLESS, "en", "fr"]))

    assert poster.source == "http://s1-en.jpg"
    assert [c.kwargs["language"] for c in aggregator.find_best_season_poster.call_args_list] == [None, "en"]
