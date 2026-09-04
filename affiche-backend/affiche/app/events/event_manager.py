import asyncio
import json
import logging
import threading
from typing import Callable, Optional, Set, Dict, Any

logger = logging.getLogger(__name__)

PosterVersionResolver = Callable[[int, int, Optional[int]], Optional[str]]

SSE_QUEUE_MAXSIZE = 1000

class EventManager:

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._poster_version: Optional[PosterVersionResolver] = None
        self._dropped: Dict[asyncio.Queue, int] = {}

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=SSE_QUEUE_MAXSIZE)
        with self._lock:
            self._subscribers.add(queue)
            count = len(self._subscribers)
        logger.info(f"New SSE subscriber. Total: {count}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        with self._lock:
            self._subscribers.discard(queue)
            count = len(self._subscribers)
            dropped = self._dropped.pop(queue, 0)
        if dropped:
            logger.warning("SSE subscriber disconnected after dropping %d event(s). Total: %d",
                           dropped, count)
        else:
            logger.info(f"SSE subscriber disconnected. Total: {count}")

    def publish(self, event_type: str, data: Dict[str, Any]):
        with self._lock:
            subscribers = list(self._subscribers)
        if not subscribers:
            return

        message = {
            "type": event_type,
            "data": data
        }

        loop = self._loop
        for queue in subscribers:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._safe_put, queue, message)
            else:
                self._safe_put(queue, message)

    def _safe_put(self, queue: asyncio.Queue, message: Dict[str, Any]) -> None:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            with self._lock:
                dropped = self._dropped.get(queue, 0) + 1
                self._dropped[queue] = dropped
            if dropped == 1:
                logger.warning(
                    "An SSE subscriber is not keeping up (backlog of %d events); dropping further "
                    "events for it. Its UI will catch up on the next refresh.", SSE_QUEUE_MAXSIZE)

    def set_poster_version_resolver(self, resolver: PosterVersionResolver) -> None:
        self._poster_version = resolver

    def _resolve_poster_version(self, library_id: int, item_id: int,
                                season_number: Optional[int] = None) -> Optional[str]:
        if self._poster_version is None:
            return None
        try:
            return self._poster_version(library_id, item_id, season_number)
        except Exception:
            logger.warning("Could not resolve poster version for %s/%s", library_id, item_id,
                           exc_info=True)
            return None

    def publish_item_processed(self, library_id: int, item_id: int, processed: bool = True):
        self.publish("item_processed", {
            "library_id": library_id,
            "item_id": item_id,
            "processed": processed,
            "poster_version": self._resolve_poster_version(library_id, item_id),
        })

    def publish_season_processed(self, library_id: int, item_id: int, season_number: int, processed: bool = True):
        self.publish("season_processed", {
            "library_id": library_id,
            "item_id": item_id,
            "season_number": season_number,
            "processed": processed,
            "poster_version": self._resolve_poster_version(library_id, item_id, season_number),
        })

    def publish_library_synced(self, media_server_id: int, library_id: int = None):
        self.publish("library_synced", {
            "media_server_id": media_server_id,
            "library_id": library_id,
        })

    def publish_task_status(self, task_id: str, status: str, task_name: str, message: str = None, error: str = None):
        self.publish("task_status", {
            "task_id": task_id,
            "status": status,
            "task_name": task_name,
            "message": message,
            "error": error
        })

    def publish_task_progress(self, task_id: str, task_name: str, current: int, total: int,
                              message: str = None):
        self.publish("task_progress", {
            "task_id": task_id,
            "task_name": task_name,
            "current": current,
            "total": total,
            "message": message,
        })

event_manager = EventManager()
