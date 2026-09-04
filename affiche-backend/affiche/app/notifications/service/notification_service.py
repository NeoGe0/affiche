import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from affiche.app.notifications.model.notification_target import (
    NotificationEvent, NotificationTarget, NotificationType,
)
from affiche.app.notifications.service.notification_target_repository import (
    NotificationTargetRepository,
)
from affiche.config.exceptions.exceptions import NotificationTargetNotFoundException
from affiche.external.notifications import notification_client

logger = logging.getLogger(__name__)

class NotificationService:

    def __init__(self, session: Session):
        self._repository = NotificationTargetRepository(session)

    def list_targets(self) -> List[NotificationTarget]:
        return self._repository.list_all()

    def get_target(self, target_id: int) -> NotificationTarget:
        target = self._repository.get(target_id)
        if not target:
            raise NotificationTargetNotFoundException(target_id)
        return target

    def create_target(self, target: NotificationTarget) -> NotificationTarget:
        return self._repository.create(target)

    def update_target(self, target_id: int, updates: Dict[str, Any]) -> NotificationTarget:
        target = self.get_target(target_id)
        updated = target.model_copy(update={k: v for k, v in updates.items() if v is not None})
        return self._repository.update(updated)

    def delete_target(self, target_id: int) -> None:
        if not self._repository.delete(target_id):
            raise NotificationTargetNotFoundException(target_id)

    def send_test(self, target_id: int) -> bool:
        target = self.get_target(target_id)
        return self.send_test_to(target.type, target.url, target.name)

    def send_test_to(self, type: NotificationType, url: str, name: str) -> bool:
        return notification_client.send(
            type, url,
            title="Affiche test notification",
            message=f'If you can read this, "{name}" is configured correctly.',
            event=NotificationEvent.TASK_COMPLETED,
            details={"test": True},
        )

    def notify(self, event: NotificationEvent, title: str, message: str,
               details: Optional[Dict[str, Any]] = None) -> int:
        targets = [t for t in self._repository.list_enabled() if t.wants(event)]
        if not targets:
            return 0

        sent = 0
        for target in targets:
            if notification_client.send(target.type, target.url, title, message, event, details):
                sent += 1
        logger.info("Notified %d/%d target(s) of %s", sent, len(targets), event.value)
        return sent

__all__ = ["NotificationService", "NotificationEvent", "NotificationTarget", "NotificationType"]
