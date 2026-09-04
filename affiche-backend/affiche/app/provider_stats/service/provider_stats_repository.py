from datetime import date
from typing import List

from sqlalchemy.orm import Session

from affiche.app.provider_stats.connector.alchemy_provider_hit_connector import (
    AlchemyProviderHitConnector,
)
from affiche.app.provider_stats.model.provider_hit import ProviderDay, ProviderStatsQuery

class ProviderStatsRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyProviderHitConnector(session)

    def increment(self, day: date, provider: str, library_id: int, by: int = 1) -> bool:
        return self._connector.increment(day, provider, library_id, by)

    def sum_by_day(self, query: ProviderStatsQuery) -> List[ProviderDay]:
        return self._connector.sum_by_day(query)

    def sum_by_provider(self, query: ProviderStatsQuery) -> dict[str, int]:
        return self._connector.sum_by_provider(query)

    def prune(self, before: date) -> int:
        return self._connector.prune(before)
