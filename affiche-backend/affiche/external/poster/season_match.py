import re
from typing import Iterable, List, NamedTuple, Optional

from affiche.external.poster.provider.base_provider import SeriesFacts, SeriesSeason

_GENERIC = re.compile(
    r"^(season|saison|serie|series|staffel|temporada|stagione|seizoen|sezon)?\s*0*(\d+)?$",
    re.IGNORECASE)
_SPECIALS = re.compile(r"^(specials?|extras?|hors[- ]s[ée]rie)$", re.IGNORECASE)

YEAR_SLACK = 1

class SeasonMatchSuggestion(NamedTuple):
    tmdb_id: int
    season_number: int
    series_name: str
    reason: str

def is_distinctive(name: Optional[str], season_number: int) -> bool:
    text = (name or "").strip()
    if not text or _SPECIALS.match(text):
        return False
    match = _GENERIC.match(text)
    if not match:
        return True
    number = match.group(2)
    return number is not None and int(number) != season_number and match.group(1) is None

def missing_seasons(facts: Optional[SeriesFacts],
                    library_season_numbers: Iterable[int]) -> List[int]:
    if facts is None:
        return []
    theirs = {season.number for season in facts.seasons if season.number != 0}
    return sorted({n for n in library_season_numbers if n != 0} - theirs)

def pick_season(candidate: SeriesFacts, target: SeriesSeason) -> Optional[SeriesSeason]:
    seasons = [s for s in candidate.seasons if s.number != 0]
    if not seasons:
        return None

    by_episodes = [s for s in seasons if _episodes_agree(s, target)]
    dated = [s for s in (by_episodes or seasons) if _years_agree(s, target, candidate)]

    if len(seasons) == 1:
        return seasons[0] if dated or _nothing_to_check(target) else None
    if len(by_episodes) == 1 and (dated or _nothing_to_check(target)):
        return by_episodes[0]
    if len(dated) == 1 and by_episodes:
        return dated[0]
    return None

def describe(candidate: SeriesFacts, season: SeriesSeason, target: SeriesSeason) -> str:
    parts = []
    if season.episode_count and target.episode_count:
        parts.append(f"{season.episode_count} episodes")
    year = season.year or candidate.year
    if year:
        parts.append(str(year))
    detail = f" ({', '.join(parts)})" if parts else ""
    return f"Matched “{target.name}” to {candidate.name}{detail}"

def queries(show_title: str, season_name: str) -> List[str]:
    name = season_name.strip()
    show = show_title.strip()
    if not show or name.lower().startswith(show.lower()):
        return [name]
    return [f"{show}: {name}", name]

def _episodes_agree(season: SeriesSeason, target: SeriesSeason) -> bool:
    return (season.episode_count is not None
            and target.episode_count is not None
            and season.episode_count == target.episode_count)

def _years_agree(season: SeriesSeason, target: SeriesSeason, candidate: SeriesFacts) -> bool:
    theirs = season.year or candidate.year
    return (theirs is not None
            and target.year is not None
            and abs(theirs - target.year) <= YEAR_SLACK)

def _nothing_to_check(target: SeriesSeason) -> bool:
    return target.year is None and target.episode_count is None
