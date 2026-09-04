import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class InternalEventBus:

    def __init__(self):
        self._handlers: Dict[str, List[Callable[..., None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[..., None]) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("Subscribed handler to event '%s'", event_type)

    def unsubscribe(self, event_type: str, handler: Callable[..., None]) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    def publish(self, event_type: str, **kwargs: Any) -> None:
        if event_type not in self._handlers:
            return

        for handler in self._handlers[event_type]:
            try:
                handler(**kwargs)
            except Exception:
                logger.exception(
                    "Error in event handler for '%s'", event_type
                )

    def publish_media_server_updated(self, media_server_id: int) -> None:
        self.publish("media_server.updated", media_server_id=media_server_id)

    def publish_media_server_deleted(self, media_server_id: int) -> None:
        self.publish("media_server.deleted", media_server_id=media_server_id)

    def publish_task_finished(self, task_id: str, task_name: str, status: str,
                              error: str = None) -> None:
        self.publish("task.finished", task_id=task_id, task_name=task_name, status=status,
                     error=error)

internal_event_bus = InternalEventBus()
