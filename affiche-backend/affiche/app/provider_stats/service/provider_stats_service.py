import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.provider_stats.model.provider_hit import (
    DEFAULT_WINDOW_DAYS,
    RETENTION_DAYS,
    ProviderDay,
    ProviderStatsQuery,
)
from affiche.app.provider_stats.service.provider_stats_repository import ProviderStatsRepository

logger = logging.getLogger(__name__)

__all__ = ["ProviderStatsService", "DEFAULT_WINDOW_DAYS", "RETENTION_DAYS"]

class ProviderStatsService:

    def __init__(self, session: Session):
        self._repo = ProviderStatsRepository(session)

    def record(self, provider: Optional[str], library_id: int, day: Optional[date] = None) -> None:
        if not provider:
            return
        try:
            created = self._repo.increment(day or date.today(), provider, library_id)
            if created:
                self._repo.prune(date.today() - timedelta(days=RETENTION_DAYS))
        except Exception:
            logger.exception("Could not count a %s poster for library %s", provider, library_id)

    def daily(self, query: ProviderStatsQuery) -> List[ProviderDay]:
        return self._repo.sum_by_day(query)

    def totals(self, query: ProviderStatsQuery) -> dict[str, int]:
        return self._repo.sum_by_provider(query)
