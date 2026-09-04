from typing import List, Optional

import pytest

from affiche.app.service_configuration.exceptions import NoProvidersConfiguredError
from affiche.external.poster.poster_service import PosterAggregatorService, ProviderPoster
from affiche.external.poster.provider.base_provider import ExternalProvider

class StubProvider(ExternalProvider):

    def __init__(self, name: str, poster: Optional[str] = None, title: Optional[str] = None,
                 search_id: Optional[str] = None, raises: bool = False,
                 posters: Optional[List[str]] = None):
        self._name = name
        self._poster = poster
        self._posters = posters
        self._title = title
        self._search_id = search_id
        self._raises = raises
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    def _answer(self, value):
        self.calls += 1
        if self._raises:
            raise RuntimeError(f"{self._name} exploded")
        return value

    def get_movie_poster(self, tmdb_id=None, tvdb_id=None, language=None) -> Optional[str]:
        return self._answer(self._poster)

    def get_show_poster(self, tmdb_id=None, tvdb_id=None, language=None) -> Optional[str]:
        return self._answer(self._poster)

    def get_season_poster(self, season_number, tmdb_id=None, tvdb_id=None,
                          language=None) -> Optional[str]:
        return self._answer(self._poster)

    def _all(self) -> List[str]:
        if self._posters is not None:
            return self._posters
        return [self._poster] if self._poster else []

    def get_all_posters(self, media_type, tmdb_id=None, tvdb_id=None,
                        language=None) -> List[str]:
        return self._answer(self._all())

    def get_all_season_posters(self, season_number, tmdb_id=None, tvdb_id=None,
                               language=None) -> List[str]:
        return self._answer(self._all())

    def search_by_title(self, title, media_type, year=None) -> Optional[str]:
        return self._answer(self._search_id)

    def get_translated_title(self, media_type, language, tmdb_id=None, tvdb_id=None,
                             season_number=None) -> Optional[str]:
        return self._answer(self._title)

    def test_connection(self, api_token) -> bool:
        return True

ORDER = ["tmdb", "tvdb"]

def _found(result):
    return (result.url, result.provider) if result else None

def test_rejects_an_empty_provider_list():
    with pytest.raises(NoProvidersConfiguredError):
        PosterAggregatorService([])

class TestGetBestPoster:
    def test_a_raising_provider_falls_through_to_the_next(self):
        broken = StubProvider("tmdb", raises=True)
        working = StubProvider("tvdb", poster="http://tvdb/poster.jpg")
        aggregator = PosterAggregatorService([broken, working])

        result = aggregator.find_best_poster(title="T", tmdb_id=1, tvdb_id=2,
                                            media_type="movie", provider_order=ORDER)

        assert _found(result) == ("http://tvdb/poster.jpg", "tvdb")
        assert broken.calls == 1

    def test_shows_take_the_same_path(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", raises=True),
            StubProvider("tvdb", poster="http://tvdb/show.jpg"),
        ])

        assert _found(aggregator.find_best_poster(title="T", tmdb_id=1, tvdb_id=2, media_type="show",
                                          provider_order=ORDER)) == ("http://tvdb/show.jpg", "tvdb")

    def test_every_provider_failing_is_a_miss_not_a_crash(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", raises=True),
            StubProvider("tvdb", raises=True),
        ])

        assert aggregator.find_best_poster(title="T", tmdb_id=1, tvdb_id=2, media_type="movie",
                                          provider_order=ORDER) is None

    def test_a_working_first_provider_still_short_circuits(self):
        first = StubProvider("tmdb", poster="http://tmdb/poster.jpg")
        second = StubProvider("tvdb", poster="http://tvdb/poster.jpg")
        aggregator = PosterAggregatorService([first, second])

        result = aggregator.find_best_poster(title="T", tmdb_id=1, tvdb_id=2,
                                            media_type="movie", provider_order=ORDER)

        assert _found(result) == ("http://tmdb/poster.jpg", "tmdb")
        assert second.calls == 0

class TestGetBestSeasonPoster:
    def test_a_raising_provider_falls_through_to_the_next(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", raises=True),
            StubProvider("tvdb", poster="http://tvdb/s1.jpg"),
        ])

        assert _found(aggregator.find_best_season_poster(
            title="T", tmdb_id=1, tvdb_id=2, season_number=1,
            provider_order=ORDER)) == ("http://tvdb/s1.jpg", "tvdb")

class TestBrowseCalls:

    def test_get_all_posters_keeps_the_working_providers_results(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", raises=True),
            StubProvider("tvdb", poster="http://tvdb/poster.jpg"),
        ])

        assert aggregator.get_all_posters(media_type="movie", tmdb_id=1) == \
               [ProviderPoster("http://tvdb/poster.jpg", "tvdb")]

    def test_get_all_season_posters_keeps_the_working_providers_results(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", raises=True),
            StubProvider("tvdb", poster="http://tvdb/s1.jpg"),
        ])

        assert aggregator.get_all_season_posters(season_number=1, tvdb_id=2) == \
               [ProviderPoster("http://tvdb/s1.jpg", "tvdb")]

    def test_every_poster_is_tagged_with_the_provider_that_served_it(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", poster="http://tmdb/poster.jpg"),
            StubProvider("tvdb", poster="http://tvdb/poster.jpg"),
        ])

        assert [p.provider for p in aggregator.get_all_posters(media_type="movie", tmdb_id=1)] == \
               ["tmdb", "tvdb"]

    def test_a_named_provider_is_the_only_one_asked(self):
        tmdb = StubProvider("tmdb", poster="http://tmdb/poster.jpg")
        tvdb = StubProvider("tvdb", poster="http://tvdb/poster.jpg")
        aggregator = PosterAggregatorService([tmdb, tvdb])

        assert aggregator.get_all_posters(media_type="movie", tmdb_id=1,
                                          provider_name="tvdb") == \
               [ProviderPoster("http://tvdb/poster.jpg", "tvdb")]
        assert tmdb.calls == 0

    def test_an_unknown_provider_name_asks_nobody(self):
        tmdb = StubProvider("tmdb", poster="http://tmdb/poster.jpg")
        aggregator = PosterAggregatorService([tmdb])

        assert aggregator.get_all_posters(media_type="movie", tmdb_id=1,
                                          provider_name="nope") == []
        assert tmdb.calls == 0

class TestBrowseRanking:

    def test_rank_follows_the_order_the_provider_answered_in(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", posters=["a.jpg", "b.jpg", "c.jpg"]),
        ])

        assert [(p.rank, p.rank_score)
                for p in aggregator.get_all_posters(media_type="movie", tmdb_id=1)] ==                [(0, 1.0), (1, 0.5), (2, 0.0)]

    def test_rank_restarts_for_each_provider(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", posters=["a.jpg", "b.jpg"]),
            StubProvider("tvdb", posters=["c.jpg", "d.jpg"]),
        ])

        assert [(p.provider, p.rank)
                for p in aggregator.get_all_posters(media_type="movie", tmdb_id=1)] ==                [("tmdb", 0), ("tmdb", 1), ("tvdb", 0), ("tvdb", 1)]

    def test_a_lone_result_is_its_providers_best(self):
        aggregator = PosterAggregatorService([StubProvider("shoko", posters=["only.jpg"])])

        assert aggregator.get_all_posters(media_type="movie", tmdb_id=1)[0].rank_score == 1.0

    def test_a_short_list_still_spans_the_full_range(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", posters=[f"{i}.jpg" for i in range(40)]),
            StubProvider("shoko", posters=["x.jpg", "y.jpg"]),
        ])

        posters = aggregator.get_all_posters(media_type="movie", tmdb_id=1)
        by_provider = {p.provider: [c.rank_score for c in posters if c.provider == p.provider]
                       for p in posters}
        assert by_provider["tmdb"][0] == by_provider["shoko"][0] == 1.0
        assert by_provider["tmdb"][-1] == by_provider["shoko"][-1] == 0.0

    def test_season_posters_are_ranked_the_same_way(self):
        aggregator = PosterAggregatorService([StubProvider("tvdb", posters=["s1.jpg", "s2.jpg"])])

        assert [p.rank for p in aggregator.get_all_season_posters(season_number=1, tvdb_id=2)] ==                [0, 1]

class TestSearchByTitle:
    def test_a_raising_provider_does_not_lose_the_other_id(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", raises=True),
            StubProvider("tvdb", search_id="555"),
        ])

        ids = aggregator.search_by_title("Blade Runner", "movie")

        assert (ids.tmdb_id, ids.tvdb_id) == (None, 555)

    def test_a_non_numeric_id_is_a_miss_not_a_crash(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", search_id="not-an-id"),
            StubProvider("tvdb", search_id="555"),
        ])

        ids = aggregator.search_by_title("Blade Runner", "movie")

        assert (ids.tmdb_id, ids.tvdb_id) == (None, 555)

    def test_collects_ids_from_every_provider_that_answers(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", search_id="42"),
            StubProvider("tvdb", search_id="555"),
        ])

        ids = aggregator.search_by_title("Blade Runner", "movie")

        assert (ids.tmdb_id, ids.tvdb_id) == (42, 555)

class TestGetTranslatedTitle:
    def test_a_raising_provider_falls_through_to_the_next(self):
        aggregator = PosterAggregatorService([
            StubProvider("tmdb", raises=True),
            StubProvider("tvdb", title="Blade Runner"),
        ])

        assert aggregator.get_translated_title(media_type="movie", language="fr",
                                               tvdb_id=2) == "Blade Runner"

class CollectionStub(ExternalProvider):

    supports_collections = True

    def __init__(self, name: str, by_member: dict, raises: bool = False):
        self._name = name
        self._by_member = by_member
        self._raises = raises
        self.asked: List[int] = []

    @property
    def name(self) -> str:
        return self._name

    def find_collection_id(self, movie_tmdb_id: int) -> Optional[int]:
        self.asked.append(movie_tmdb_id)
        if self._raises:
            raise RuntimeError(f"{self._name} exploded")
        return self._by_member.get(movie_tmdb_id)

    def get_movie_poster(self, tmdb_id=None, tvdb_id=None, language=None): return None
    def get_show_poster(self, tmdb_id=None, tvdb_id=None, language=None): return None
    def get_season_poster(self, season_number, tmdb_id=None, tvdb_id=None, language=None): return None
    def get_all_posters(self, media_type, tmdb_id=None, tvdb_id=None, language=None): return []
    def get_all_season_posters(self, season_number, tmdb_id=None, tvdb_id=None, language=None): return []
    def test_connection(self, api_token) -> bool: return True

class TestCollectionConsensus:

    def test_two_agreeing_members_settle_it(self):
        provider = CollectionStub("tmdb", {11: 10, 1893: 10})
        assert PosterAggregatorService([provider]).find_collection_id([11, 1893]) == 10

    def test_a_single_vote_is_not_enough(self):
        provider = CollectionStub("tmdb", {11: 10})
        assert PosterAggregatorService([provider]).find_collection_id([11, 1893]) is None

    def test_one_mismatched_member_cannot_carry_the_collection(self):
        provider = CollectionStub("tmdb", {671: 1241, 11: 10, 1893: 10})
        assert PosterAggregatorService([provider]).find_collection_id([671, 11, 1893]) == 10

    def test_a_lone_mismatch_settles_nothing(self):
        provider = CollectionStub("tmdb", {671: 1241, 11: 10})
        assert PosterAggregatorService([provider]).find_collection_id([671, 11]) is None

    def test_it_stops_asking_once_a_collection_has_enough_votes(self):
        provider = CollectionStub("tmdb", {11: 10, 1893: 10, 1892: 10})
        PosterAggregatorService([provider]).find_collection_id([11, 1893, 1892])
        assert provider.asked == [11, 1893]

    def test_votes_from_different_providers_count_together(self):
        tmdb = CollectionStub("tmdb", {11: 10})
        mediux = CollectionStub("mediux", {1893: 10})
        assert PosterAggregatorService([tmdb, mediux]).find_collection_id([11, 1893]) == 10

    def test_a_provider_without_the_capability_is_never_asked(self):
        plain = StubProvider("fanart")
        collections = CollectionStub("tmdb", {11: 10, 1893: 10})
        assert PosterAggregatorService([plain, collections]).find_collection_id([11, 1893]) == 10
        assert plain.calls == 0

    def test_a_failing_provider_does_not_stop_the_others(self):
        broken = CollectionStub("tmdb", {}, raises=True)
        working = CollectionStub("mediux", {11: 10, 1893: 10})
        assert PosterAggregatorService([broken, working]).find_collection_id([11, 1893]) == 10
