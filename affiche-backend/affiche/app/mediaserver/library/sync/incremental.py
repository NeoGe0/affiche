from datetime import datetime, timedelta, timezone
from typing import Optional

RECENT_ITEM_LIMIT = 50

FULL_SYNC_MAX_AGE = timedelta(hours=24)

def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

def may_run_incrementally(last_full_sync_at: Optional[datetime], now: datetime) -> bool:
    if last_full_sync_at is None:
        return False
    return as_utc(last_full_sync_at) + FULL_SYNC_MAX_AGE > as_utc(now)
