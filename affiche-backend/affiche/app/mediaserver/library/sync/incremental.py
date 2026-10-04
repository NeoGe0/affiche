from datetime import datetime, timedelta, timezone
from typing import Collection, List, Mapping, Optional

RECENT_ITEM_LIMIT = 50

FULL_SYNC_MAX_AGE = timedelta(hours=24)

def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

def may_run_incrementally(last_full_sync_at: Optional[datetime], now: datetime) -> bool:
    if last_full_sync_at is None:
        return False
    return as_utc(last_full_sync_at) + FULL_SYNC_MAX_AGE > as_utc(now)

def shows_gaining_seasons(recent_seasons: Mapping[str, str],
                          known_season_ids: Collection[str],
                          listed_show_ids: Collection[str]) -> Optional[List[str]]:
    new = {season: show for season, show in recent_seasons.items()
           if season not in known_season_ids}
    if len(new) >= RECENT_ITEM_LIMIT:
        return None
    return list(dict.fromkeys(show for show in new.values() if show not in listed_show_ids))
