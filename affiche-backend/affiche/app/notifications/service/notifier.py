import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from affiche.app.events import internal_event_bus
from affiche.app.mediaserver.library.model import LibraryItemSearch, LibrarySearch
from affiche.app.notifications.model.notification_target import NotificationEvent
from affiche.app.notifications.service.notification_service import NotificationService
from affiche.config.database import SessionLocal

logger = logging.getLogger(__name__)

TASK_FINISHED_EVENT = "task.finished"

class Notifier:

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="notifier")
        self._subscribed = False

    def start(self) -> None:
        if self._subscribed:
            return
        internal_event_bus.subscribe(TASK_FINISHED_EVENT, self._on_task_finished)
        self._subscribed = True
        logger.info("Notifier subscribed to %s", TASK_FINISHED_EVENT)

    def stop(self) -> None:
        internal_event_bus.unsubscribe(TASK_FINISHED_EVENT, self._on_task_finished)
        self._subscribed = False
        self._executor.shutdown(wait=False)

    def _on_task_finished(self, task_id: str, task_name: str, status: str,
                          error: Optional[str] = None) -> None:
        self._executor.submit(self._deliver, task_id, task_name, status, error)

    def _deliver(self, task_id: str, task_name: str, status: str,
                 error: Optional[str]) -> None:
        try:
            session = SessionLocal()
            try:
                service = NotificationService(session)
                event, title, message = self._compose(task_name, status, error, session)
                service.notify(event, title, message, details={
                    "task_id": task_id,
                    "task_name": task_name,
                    "status": status,
                    "error": error,
                })
            finally:
                session.close()
        except Exception:
            logger.exception("Could not deliver notifications for task %s", task_id)

    @staticmethod
    def _compose(task_name: str, status: str, error: Optional[str], session):
        if status == "failed":
            return (NotificationEvent.TASK_FAILED,
                    f"Affiche: {task_name} failed",
                    error or "The task failed without an error message.")

        errored = Notifier._errored_items(session)
        if errored:
            return (NotificationEvent.ITEMS_ERRORED,
                    f"Affiche: {task_name} finished with errors",
                    f"{errored} item(s) are in an error state.")
        return (NotificationEvent.TASK_COMPLETED,
                f"Affiche: {task_name} finished",
                "Completed successfully.")

    @staticmethod
    def _errored_items(session) -> int:
        from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
        try:
            from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository

            repo = LibraryRepository(session)
            library_ids = [library.id
                           for server in MediaServerRepository(session).find_all()
                           for library in repo.find_libraries(LibrarySearch(media_server_id=server.id))]
            if not library_ids:
                return 0
            return repo.count_status_buckets(LibraryItemSearch(library_ids=library_ids)).errors
        except Exception:
            logger.warning("Could not count errored items for the notification", exc_info=True)
            return 0

notifier = Notifier()
