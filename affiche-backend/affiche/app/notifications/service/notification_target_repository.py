from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.notifications.connector.alchemy_notification_target_connector import (
    AlchemyNotificationTargetConnector,
)
from affiche.app.notifications.model.notification_target import NotificationTarget

class NotificationTargetRepository:

    def __init__(self, session: Session):
        self._connector = AlchemyNotificationTargetConnector(session)

    def get(self, target_id: int) -> Optional[NotificationTarget]:
        return self._connector.get(target_id)

    def list_all(self) -> List[NotificationTarget]:
        return self._connector.list_all()

    def list_enabled(self) -> List[NotificationTarget]:
        return self._connector.list_enabled()

    def create(self, target: NotificationTarget) -> NotificationTarget:
        return self._connector.create(target)

    def update(self, target: NotificationTarget) -> NotificationTarget:
        return self._connector.update(target)

    def delete(self, target_id: int) -> bool:
        return self._connector.delete(target_id)
