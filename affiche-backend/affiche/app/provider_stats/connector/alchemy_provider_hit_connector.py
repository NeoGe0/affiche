from datetime import date
from typing import List

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from affiche.app.provider_stats.connector.provider_hit_entity import ProviderHitEntity
from affiche.app.provider_stats.model.provider_hit import ProviderDay, ProviderStatsQuery

class AlchemyProviderHitConnector:

    def __init__(self, session: Session):
        self._session = session

    def increment(self, day: date, provider: str, library_id: int, by: int = 1) -> bool:
        entity = self._session.execute(
            select(ProviderHitEntity).where(
                ProviderHitEntity.day == day,
                ProviderHitEntity.provider == provider,
                ProviderHitEntity.library_id == library_id,
            )
        ).scalar_one_or_none()

        if entity is None:
            self._session.add(ProviderHitEntity(day=day, provider=provider,
                                                library_id=library_id, count=by))
            self._session.flush()
            return True

        entity.count += by
        return False

    def _scoped(self, query, search: ProviderStatsQuery):
        query = query.where(ProviderHitEntity.day >= search.since)
        if search.library_id is not None:
            query = query.where(ProviderHitEntity.library_id == search.library_id)
        return query

    def sum_by_day(self, search: ProviderStatsQuery) -> List[ProviderDay]:
        query = self._scoped(
            select(ProviderHitEntity.day, ProviderHitEntity.provider,
                   func.sum(ProviderHitEntity.count)), search)
        query = (query.group_by(ProviderHitEntity.day, ProviderHitEntity.provider)
                      .order_by(ProviderHitEntity.day, ProviderHitEntity.provider))

        return [ProviderDay(day=day, provider=provider, count=count)
                for day, provider, count in self._session.execute(query).all()]

    def sum_by_provider(self, search: ProviderStatsQuery) -> dict[str, int]:
        query = self._scoped(
            select(ProviderHitEntity.provider, func.sum(ProviderHitEntity.count)), search)
        query = query.group_by(ProviderHitEntity.provider)

        return {provider: count for provider, count in self._session.execute(query).all()}

    def prune(self, before: date) -> int:
        result = self._session.execute(
            delete(ProviderHitEntity).where(ProviderHitEntity.day < before)
        )
        return result.rowcount or 0
