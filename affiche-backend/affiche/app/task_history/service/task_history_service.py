import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.task_history.model.task_run import TaskRun, TaskRunSearch
from affiche.app.task_history.service.task_history_repository import TaskHistoryRepository
from affiche.app.task_history.task_scope import parse_task_scope

logger = logging.getLogger(__name__)

MAX_RUNS = 500

_TERMINAL = ("completed", "failed", "cancelled")

class TaskHistoryService:

    def __init__(self, session: Session):
        self._repo = TaskHistoryRepository(session)

    def record(self, task_id: str, task: dict) -> Optional[TaskRun]:
        try:
            run = self._to_run(task_id, task)
            saved = self._repo.save(run)
            if run.status in _TERMINAL:
                self._prune()
            return saved
        except Exception:
            logger.exception("Could not record task run %s", task_id)
            return None

    def find_recent(self, search: TaskRunSearch) -> List[TaskRun]:
        return self._repo.find_recent(search)

    def _prune(self) -> None:
        if self._repo.count() > MAX_RUNS:
            removed = self._repo.prune(MAX_RUNS)
            logger.debug("Pruned %d task runs over the %d cap", removed, MAX_RUNS)

    @staticmethod
    def _to_run(task_id: str, task: dict) -> TaskRun:
        media_server_id, library_id = parse_task_scope(task.get("resource"))
        progress = task.get("progress") or {}
        status = task.get("status", "pending")

        return TaskRun(
            task_id=task_id,
            task_name=task.get("task_name", "unknown"),
            status=status,
            resource=task.get("resource"),
            media_server_id=media_server_id,
            library_id=library_id,
            blocking=bool(task.get("blocking")),
            created_at=_timestamp(task.get("created_at")) or datetime.now(),
            started_at=_timestamp(task.get("started_at")),
            ended_at=_ended_at(task) if status in _TERMINAL else None,
            items_done=progress.get("current"),
            items_total=progress.get("total"),
            message=task.get("message"),
            error=task.get("error"),
        )

def _ended_at(task: dict) -> Optional[datetime]:
    for key in ("completed_at", "failed_at", "cancelled_at"):
        stamped = _timestamp(task.get(key))
        if stamped is not None:
            return stamped
    return datetime.now()

def _timestamp(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
