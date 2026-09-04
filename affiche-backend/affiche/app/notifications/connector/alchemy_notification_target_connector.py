from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from affiche.app.notifications.connector.notification_target_entity import (
    NotificationTargetEntity,
)
from affiche.app.notifications.model.notification_target import NotificationTarget

class AlchemyNotificationTargetConnector:

    def __init__(self, session: Session):
        self._session = session

    def get(self, target_id: int) -> Optional[NotificationTarget]:
        entity = self._session.get(NotificationTargetEntity, target_id)
        return NotificationTarget.model_validate(entity) if entity else None

    def list_all(self) -> List[NotificationTarget]:
        entities = (self._session.query(NotificationTargetEntity)
                    .order_by(func.lower(NotificationTargetEntity.name))
                    .all())
        return [NotificationTarget.model_validate(entity) for entity in entities]

    def list_enabled(self) -> List[NotificationTarget]:
        entities = (self._session.query(NotificationTargetEntity)
                    .filter(NotificationTargetEntity.enabled.is_(True))
                    .order_by(NotificationTargetEntity.id)
                    .all())
        return [NotificationTarget.model_validate(entity) for entity in entities]

    def create(self, target: NotificationTarget) -> NotificationTarget:
        entity = NotificationTargetEntity(
            **target.model_dump(exclude={"id", "created_at", "updated_at"}))
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return NotificationTarget.model_validate(entity)

    def update(self, target: NotificationTarget) -> NotificationTarget:
        entity = self._session.get(NotificationTargetEntity, target.id)
        if not entity:
            raise ValueError(f"Notification target {target.id} not found")

        for field, value in target.model_dump(
                exclude={"id", "created_at", "updated_at"}).items():
            setattr(entity, field, value)

        self._session.commit()
        self._session.refresh(entity)
        return NotificationTarget.model_validate(entity)

    def delete(self, target_id: int) -> bool:
        entity = self._session.get(NotificationTargetEntity, target_id)
        if not entity:
            return False

        self._session.delete(entity)
        self._session.commit()
        return True
