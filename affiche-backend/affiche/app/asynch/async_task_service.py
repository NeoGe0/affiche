import contextvars
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from uuid import uuid4
from datetime import datetime
from threading import Event, RLock
from typing import Dict, Iterator, Optional, Callable, Tuple
from fastapi import BackgroundTasks
import logging

from affiche.app.events import event_manager, internal_event_bus

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = ("completed", "failed", "cancelled")
_ACTIVE_STATUSES = ("pending", "running")

_current_progress: contextvars.ContextVar[Optional[Callable[[int, int, Optional[str]], None]]] = \
    contextvars.ContextVar("_current_progress", default=None)

_current_segment: contextvars.ContextVar[Tuple[float, float]] = \
    contextvars.ContextVar("_current_segment", default=(0.0, 100.0))

@contextmanager
def progress_segment(rel_base: float, rel_span: float) -> Iterator[None]:
    parent_base, parent_span = _current_segment.get()
    token = _current_segment.set((parent_base + rel_base * parent_span, rel_span * parent_span))
    try:
        yield
    finally:
        _current_segment.reset(token)

def report_task_progress(current: int, total: int, message: Optional[str] = None) -> None:
    reporter = _current_progress.get()
    if reporter is None:
        return
    base, span = _current_segment.get()
    frac = (current / total) if total else 0.0
    frac = max(0.0, min(1.0, frac))
    reporter(round(base + frac * span), 100, message)

class TaskConflictError(Exception):

    def __init__(self, running_task_id: str, resource: Optional[str]):
        self.running_task_id = running_task_id
        self.resource = resource
        super().__init__(
            f"A blocking task ({running_task_id}) is already running for resource '{resource}'"
        )

def _resources_conflict(a: Optional[str], b: Optional[str]) -> bool:
    if a is None or b is None:
        return False
    if a == b:
        return True
    for wildcard, other in ((a, b), (b, a)):
        if wildcard.endswith(":*") and other.startswith(wildcard[:-1]):
            return True
    return False

class AsyncTaskService:

    def __init__(self, max_tasks: int = 100,
                 history: Optional[Callable[[str, dict], None]] = None):
        self.tasks: OrderedDict[str, dict] = OrderedDict()
        self.cancel_events: Dict[str, Event] = {}
        self.max_tasks = max_tasks
        self._history = history
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="detached-task")

    def _record(self, task_id: str) -> None:
        if self._history is None:
            return
        with self._lock:
            task = self.tasks.get(task_id)
            snapshot = dict(task) if task else None
        if snapshot is None:
            return
        try:
            self._history(task_id, snapshot)
        except Exception:
            logger.exception("Could not record task run %s", task_id)

    def get_running_task(self, task_name: str) -> Optional[str]:
        with self._lock:
            for task_id, task in self.tasks.items():
                if (task.get("task_name") == task_name and
                        task.get("status") in _ACTIVE_STATUSES):
                    return task_id
        return None

    def get_running_blocking_task(self) -> Optional[dict]:
        with self._lock:
            for task_id, task in self.tasks.items():
                if (task.get("blocking") and
                        task.get("status") in _ACTIVE_STATUSES):
                    return {"task_id": task_id, **task}
        return None

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.get("status") not in _ACTIVE_STATUSES:
                return False
            event = self.cancel_events.get(task_id)
            if event:
                event.set()
            task_name = task.get("task_name", "unknown")
            task.update({
                "status": "cancelled",
                "cancelled_at": datetime.now().isoformat(),
                "message": "Task was cancelled by user"
            })

        self._record(task_id)
        event_manager.publish_task_status(task_id, "cancelled", task_name, "Task was cancelled by user")
        logger.info(f"Task cancelled: {task_id}")
        return True

    def _report_progress(self, task_id: str, task_name: str, current: int, total: int,
                         message: Optional[str] = None):
        with self._lock:
            task = self.tasks.get(task_id)
            if task is None or task.get("status") not in _ACTIVE_STATUSES:
                return
            task["progress"] = {"current": current, "total": total, "message": message}
        event_manager.publish_task_progress(task_id, task_name, current, total, message)

    def is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            event = self.cancel_events.get(task_id)
        return event.is_set() if event else False

    def submit_task(
            self,
            background_tasks: BackgroundTasks,
            task_func: Callable,
            task_name: str,
            blocking: bool = False,
            resource: Optional[str] = None,
            *args,
            **kwargs
    ) -> Tuple[str, str]:

        task_id, status = self._register_task(task_name, blocking, resource)
        if status == "running":
            return task_id, status

        background_tasks.add_task(self._run_task, task_id, task_func, *args, **kwargs)
        logger.info(f"Task submitted: {task_name} (ID: {task_id})")
        return task_id, "pending"

    def submit_detached_task(
            self,
            task_func: Callable,
            task_name: str,
            blocking: bool = False,
            resource: Optional[str] = None,
            *args,
            **kwargs
    ) -> Tuple[str, str]:
        task_id, status = self._register_task(task_name, blocking, resource)
        if status == "running":
            return task_id, status

        self._executor.submit(self._run_task, task_id, task_func, *args, **kwargs)
        logger.info(f"Detached task submitted: {task_name} (ID: {task_id})")
        return task_id, "pending"

    def _register_task(self, task_name: str, blocking: bool,
                       resource: Optional[str]) -> Tuple[str, str]:
        with self._lock:
            existing_task_id = self.get_running_task(task_name)
            if existing_task_id:
                logger.info(f"Task {task_name} already running (ID: {existing_task_id})")
                return existing_task_id, "running"

            if blocking:
                for tid, task in self.tasks.items():
                    if (task.get("blocking") and task.get("status") in _ACTIVE_STATUSES
                            and _resources_conflict(task.get("resource"), resource)):
                        logger.info(f"Blocking task {task_name} conflicts with running {tid}")
                        raise TaskConflictError(tid, resource)

            task_id = str(uuid4())
            self.cancel_events[task_id] = Event()
            self.tasks[task_id] = {
                "status": "pending",
                "task_name": task_name,
                "blocking": blocking,
                "resource": resource,
                "created_at": datetime.now().isoformat()
            }
        self._record(task_id)
        return task_id, "pending"

    def _run_task(self, task_id: str, task_func: Callable, *args, **kwargs):
        with self._lock:
            task = self.tasks.get(task_id)
            task_name = task.get("task_name", "unknown") if task else "unknown"

        try:
            if self.is_cancelled(task_id):
                logger.info(f"Task {task_id} was cancelled before starting")
                return

            with self._lock:
                task = self.tasks.get(task_id)
                if task is None:
                    return
                task.update({
                    "status": "running",
                    "started_at": datetime.now().isoformat(),
                    "message": f"Executing {task_name}..."
                })
            self._record(task_id)
            event_manager.publish_task_status(task_id, "running", task_name, f"Executing {task_name}...")

            cancel_checker = lambda: self.is_cancelled(task_id)
            progress_token = _current_progress.set(
                lambda current, total, message=None: self._report_progress(
                    task_id, task_name, current, total, message)
            )
            try:
                result = task_func(*args, cancel_check=cancel_checker, **kwargs)
            finally:
                _current_progress.reset(progress_token)

            with self._lock:
                if self.is_cancelled(task_id):
                    logger.info(f"Task {task_id} was cancelled during execution")
                    return
                task = self.tasks.get(task_id)
                if task is None or task.get("status") != "running":
                    return
                task.update({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "message": "Task completed successfully",
                    "result": result if result else None
                })
            self._record(task_id)
            event_manager.publish_task_status(task_id, "completed", task_name, "Task completed successfully")
            internal_event_bus.publish_task_finished(task_id, task_name, "completed")
            logger.info(f"Task completed: {task_id}")

        except Exception as e:
            published = False
            with self._lock:
                task = self.tasks.get(task_id)
                if (not self.is_cancelled(task_id) and task is not None
                        and task.get("status") not in _TERMINAL_STATUSES):
                    task.update({
                        "status": "failed",
                        "failed_at": datetime.now().isoformat(),
                        "error": str(e),
                        "message": f"Task failed: {str(e)}"
                    })
                    published = True
            if published:
                self._record(task_id)
                event_manager.publish_task_status(task_id, "failed", task_name, f"Task failed: {str(e)}", str(e))
                internal_event_bus.publish_task_finished(task_id, task_name, "failed", str(e))
                logger.error(f"Task failed: {task_id} - {str(e)}")

        finally:
            with self._lock:
                self.cancel_events.pop(task_id, None)
                self._cleanup_old_tasks()

    def get_task_status(self, task_id: str) -> Optional[dict]:
        with self._lock:
            task = self.tasks.get(task_id)
            return dict(task) if task else None

    def get_latest_task(self, task_name: Optional[str] = None) -> Optional[dict]:
        with self._lock:
            filtered = {
                tid: dict(task) for tid, task in self.tasks.items()
                if task_name is None or task.get("task_name") == task_name
            }
        if not filtered:
            return None
        latest_task_id = max(filtered.keys(), key=lambda k: filtered[k].get("created_at", ""))
        return {"task_id": latest_task_id, **filtered[latest_task_id]}

    def get_all_tasks(self, status: Optional[str] = None) -> list[dict]:
        with self._lock:
            tasks = [{"task_id": tid, **task} for tid, task in self.tasks.items()]
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)

    def _cleanup_old_tasks(self):
        removable = [tid for tid, task in self.tasks.items()
                     if task.get("status") in _TERMINAL_STATUSES]
        excess = len(self.tasks) - self.max_tasks
        for tid in removable:
            if excess <= 0:
                break
            del self.tasks[tid]
            excess -= 1
