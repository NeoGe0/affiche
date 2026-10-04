from typing import List, Optional

import pytest

from affiche.external.poster.poster_service import PosterAggregatorService
from affiche.external.poster.season_match import (
    describe,
    is_distinctive,
    pick_season,
    queries,
)
from affiche.external.poster.provider.base_provider import (
    ExternalProvider,
    SeriesFacts,
    SeriesSeason,
)

@pytest.mark.parametrize("name", [
    "Season 2", "season 2", "Saison 2", "Staffel 2", "Temporada 2", "Seizoen 2", "Series 2",
    "Specials", "Extras", "", "   ", None,
])
def test_generic_names_are_not_distinctive(name):
    assert is_distinctive(name, 2) is False

@pytest.mark.parametrize("name", [
    "The Lyle and Erik Menendez Story",
    "Dahmer: The Jeffrey Dahmer Story",
    "The Ed Gein Story",
    "Season of the Witch",
])
def test_real_titles_are_distinctive(name):
    assert is_distinctive(name, 2) is True

def test_a_bare_number_matching_the_season_is_not_a_name():
    assert is_distinctive("2", 2) is False

MENENDEZ = SeriesSeason(number=2, name="The Lyle and Erik Menendez Story",
                        episode_count=9, year=2024)

def _single(season_year=2024, episodes=9, series_year=2024):
    return SeriesFacts(id=225634, name="Monsters: The Lyle and Erik Menendez Story",
                       year=series_year,
                       seasons=[SeriesSeason(number=1, episode_count=episodes, year=season_year)])

def test_a_lone_agreeing_season_is_the_answer():
    picked = pick_season(_single(), MENENDEZ)
    assert picked is not None and picked.number == 1

def test_the_season_number_is_confirmed_not_assumed():
    whole = SeriesFacts(id=1, name="Monster", year=2022, seasons=[
        SeriesSeason(number=1, episode_count=10, year=2022),
        SeriesSeason(number=2, episode_count=9, year=2024),
        SeriesSeason(number=3, episode_count=8, year=2025),
    ])
    picked = pick_season(whole, MENENDEZ)
    assert picked is not None and picked.number == 2

def test_a_wrong_year_is_refused():
    assert pick_season(_single(season_year=2019, series_year=2019), MENENDEZ) is None

def test_a_wrong_episode_count_with_several_seasons_is_refused():
    ambiguous = SeriesFacts(id=1, name="Monster", year=2024, seasons=[
        SeriesSeason(number=1, episode_count=6, year=2024),
        SeriesSeason(number=2, episode_count=7, year=2024),
    ])
    assert pick_season(ambiguous, MENENDEZ) is None

def test_specials_are_never_the_answer():
    only_specials = SeriesFacts(id=1, name="Monster", year=2024,
                                seasons=[SeriesSeason(number=0, episode_count=9, year=2024)])
    assert pick_season(only_specials, MENENDEZ) is None

def test_a_year_within_the_slack_still_agrees():
    picked = pick_season(_single(season_year=2025, series_year=2025), MENENDEZ)
    assert picked is not None

def test_a_lone_season_carries_the_match_when_tvdb_said_nothing():
    nameless_target = SeriesSeason(number=2, name="The Ed Gein Story")
    picked = pick_season(_single(season_year=None, episodes=None, series_year=None),
                         nameless_target)
    assert picked is not None and picked.number == 1

def test_the_show_qualifies_the_search_first():
    assert queries("Monster", "The Ed Gein Story") == [
        "Monster: The Ed Gein Story", "The Ed Gein Story"]

def test_a_name_already_carrying_the_show_is_not_doubled():
    assert queries("Monster", "Monster: The Ed Gein Story") == ["Monster: The Ed Gein Story"]

def test_the_reason_names_both_sides():
    reason = describe(_single(), SeriesSeason(number=1, episode_count=9, year=2024), MENENDEZ)
    assert "The Lyle and Erik Menendez Story" in reason
    assert "9 episodes" in reason and "2024" in reason

class StubProvider(ExternalProvider):
    def __init__(self, name: str, season=None, found=None, described=None, raises=False):
        self._name = name
        self._season = season
        self._found = found or {}
        self._described = described or {}
        self._raises = raises
        self.searched: List[str] = []

    @property
    def name(self) -> str:
        return self._name

    def describe_season(self, season_number, tmdb_id=None, tvdb_id=None):
        if self._raises:
            raise RuntimeError("tvdb is down")
        return self._season

    def find_series(self, title, year=None):
        self.searched.append(title)
        return self._found.get(title, [])

    def describe_series(self, series_id):
        return self._described.get(series_id)

    def get_movie_poster(self, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_show_poster(self, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_season_poster(self, season_number, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_all_posters(self, media_type, tmdb_id=None, tvdb_id=None, language=None):
        return []

    def get_all_season_posters(self, season_number, tmdb_id=None, tvdb_id=None, language=None):
        return []

    def test_connection(self, api_token) -> bool:
        return True

def _aggregator(season=MENENDEZ, raises=False):
    tvdb = StubProvider("tvdb", season=season, raises=raises)
    tmdb = StubProvider(
        "tmdb",
        found={"Monster: The Lyle and Erik Menendez Story": [_single()]},
        described={225634: _single()},
    )
    return tvdb, tmdb, PosterAggregatorService([tmdb, tvdb])

def test_the_whole_chain_resolves_monster_season_2():
    _, tmdb, aggregator = _aggregator()

    found = aggregator.suggest_season_match("Monster", season_number=2, tvdb_id=389492)

    assert found is not None
    assert (found.tmdb_id, found.season_number) == (225634, 1)
    assert tmdb.searched[0] == "Monster: The Lyle and Erik Menendez Story"

def test_a_generic_season_name_is_never_searched():
    _, tmdb, aggregator = _aggregator(season=SeriesSeason(number=2, name="Season 2",
                                                          episode_count=9, year=2024))

    assert aggregator.suggest_season_match("Monster", season_number=2, tvdb_id=389492) is None
    assert tmdb.searched == []

def test_no_tvdb_id_means_no_suggestion():
    _, _, aggregator = _aggregator()
    assert aggregator.suggest_season_match("Monster", season_number=2, tvdb_id=None) is None

def test_a_failing_tvdb_degrades_to_no_suggestion(caplog):
    _, _, aggregator = _aggregator(raises=True)
    assert aggregator.suggest_season_match("Monster", season_number=2, tvdb_id=389492) is None
