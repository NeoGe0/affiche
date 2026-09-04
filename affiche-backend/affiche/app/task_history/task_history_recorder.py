import logging
from typing import Callable

from affiche.app.task_history.service.task_history_service import TaskHistoryService

logger = logging.getLogger(__name__)

TaskRecorder = Callable[[str, dict], None]

def make_task_recorder(session_factory) -> TaskRecorder:

    def record(task_id: str, task: dict) -> None:
        session = session_factory()
        try:
            TaskHistoryService(session).record(task_id, task)
        except Exception:
            logger.exception("Could not open a session to record task run %s", task_id)
        finally:
            session.close()

    return record
