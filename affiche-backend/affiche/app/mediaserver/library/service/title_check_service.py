import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Callable, Dict, NamedTuple

from sqlalchemy.orm import Session

from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.mediaserver.library.model import LibraryItemSearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository

logger = logging.getLogger(__name__)

class TitleCheckReport(NamedTuple):
    checked: int = 0
    mismatched: int = 0
    skipped: int = 0

class CheckProgress(NamedTuple):
    running: bool = False
    checked: int = 0
    total: int = 0
    mismatched: int = 0

class TitleCheckService:

    def __init__(self,
                 session_factory: Callable[[], Session],
                 rename_service_factory: Callable[[Session], object]):
        self._session_factory = session_factory
        self._rename_service_factory = rename_service_factory
        self._progress: Dict[int, CheckProgress] = {}
        self._lock = Lock()

    def progress(self, library_id: int) -> CheckProgress:
        with self._lock:
            return self._progress.get(library_id, CheckProgress())

    def check_library(self,
                      media_server_id: int,
                      library_id: int,
                      force: bool = False,
                      cancel_check: Callable[[], bool] = None) -> TitleCheckReport:
        with self._session() as session:
            search = (LibraryItemSearch(library_id=library_id) if force
                      else LibraryItemSearch(library_id=library_id, title_unchecked=True))
            pending = LibraryRepository(session).find_items(search)

        if not pending:
            self._publish(library_id, CheckProgress(running=False))
            return TitleCheckReport()

        logger.info("[title-check] library %s: %d titles to check%s", library_id, len(pending),
                    " (forced)" if force else "")
        report = TitleCheckReport()
        self._publish(library_id, CheckProgress(running=True, total=len(pending)))
        try:
            for index, item in enumerate(pending):
                if cancel_check and cancel_check():
                    logger.info("[title-check] cancelled after %d items", index)
                    break
                report = self._check_item(media_server_id, item, report)
                self._publish(library_id, CheckProgress(
                    running=True, checked=index + 1, total=len(pending),
                    mismatched=report.mismatched))
                report_task_progress(index + 1, len(pending), "Titles")
        finally:
            self._publish(library_id, CheckProgress(
                running=False, checked=report.checked + report.skipped, total=len(pending),
                mismatched=report.mismatched))

        logger.info("[title-check] library %s: %d checked, %d disagree, %d skipped",
                    library_id, report.checked, report.mismatched, report.skipped)
        return report

    def _publish(self, library_id: int, progress: CheckProgress) -> None:
        with self._lock:
            self._progress[library_id] = progress

    def _check_item(self, media_server_id: int, item, report: TitleCheckReport) -> TitleCheckReport:
        try:
            with self._session() as session:
                service = self._rename_service_factory(session)
                matched = service.catalogue_title(media_server_id, item.library_id, item.id)

                if matched is None:
                    return report._replace(skipped=report.skipped + 1)

                mismatched = not service.agrees_with_catalogue(
                    media_server_id, item.library_id, item, matched.title)
                self._record(session, item, mismatched, matched)

            if mismatched:
                logger.info("[title-check] %s: %s calls it '%s'", item.title, matched.provider,
                            matched.title)
            return report._replace(checked=report.checked + 1,
                                   mismatched=report.mismatched + (1 if mismatched else 0))
        except Exception:
            logger.exception("[title-check] %s (%s): FAILED", item.id, item.title)
            return report._replace(skipped=report.skipped + 1)

    @staticmethod
    def _record(session: Session, item, mismatched: bool, matched) -> None:
        item.title_mismatched = mismatched
        item.catalogue_title = matched.title
        item.catalogue_provider = matched.provider
        item.title_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        LibraryRepository(session).create_or_update_item(item)

    @contextmanager
    def _session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()
