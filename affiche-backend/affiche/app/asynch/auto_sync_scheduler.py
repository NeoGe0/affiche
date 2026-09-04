import logging
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from typing import Optional

from sqlalchemy import select

from affiche.app.asynch.auto_pickup import dispatch_library_pickup
from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity
from affiche.app.mediaserver.library.connector.library_entity import LibraryEntity
from affiche.app.mediaserver.library.settings.connector.library_settings_entity import (
    LibrarySettingsEntity,
)
from affiche.app.mediaserver.library.settings.model.library_settings import AutoPickupAction
from affiche.app.mediaserver.library.sync.incremental import as_utc, may_run_incrementally
from affiche.config.database import SessionLocal
from affiche.config.dependencies import container

logger = logging.getLogger(__name__)

TICK_SECONDS = 60

def _is_due(last_auto_sync_at: Optional[datetime], interval_minutes: int, now: datetime) -> bool:
    if last_auto_sync_at is None:
        return True
    return as_utc(last_auto_sync_at) + timedelta(minutes=interval_minutes) <= as_utc(now)

class AutoSyncScheduler:

    def __init__(self):
        self._stop = Event()
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="auto-sync-scheduler", daemon=True)
        self._thread.start()
        logger.info("Auto-sync scheduler started (tick=%ds)", TICK_SECONDS)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Auto-sync scheduler stopped")

    def _run(self) -> None:
        while not self._stop.wait(TICK_SECONDS):
            try:
                self.tick()
            except Exception:
                logger.exception("Auto-sync scheduler tick failed")

    def tick(self) -> None:
        now = datetime.now(timezone.utc)
        task_service = container.async_task_service

        session = SessionLocal()
        try:
            stmt = (
                select(LibrarySettingsEntity, LibraryEntity)
                .join(LibraryEntity, LibraryEntity.id == LibrarySettingsEntity.library_id)
                .join(MediaServerEntity, MediaServerEntity.id == LibraryEntity.media_server_id)
                .where(
                    LibrarySettingsEntity.auto_sync_enabled.is_(True),
                    LibraryEntity.enabled.is_(True),
                    MediaServerEntity.enabled.is_(True),
                )
            )
            rows = session.execute(stmt).all()

            for settings, library in rows:
                if not _is_due(settings.last_auto_sync_at,
                               settings.auto_sync_interval_minutes, now):
                    continue

                action = AutoPickupAction(settings.auto_pickup_action)
                incremental = may_run_incrementally(settings.last_full_sync_at, now)
                result = dispatch_library_pickup(
                    task_service, library.media_server_id, library.id, action,
                    incremental=incremental)
                if result is None:
                    continue

                settings.last_auto_sync_at = now
                session.commit()
                logger.info("Auto-pickup dispatched for library %d (action=%s, mode=%s)",
                            library.id, action.value,
                            "incremental" if incremental else "full")
        finally:
            session.close()

auto_sync_scheduler = AutoSyncScheduler()
