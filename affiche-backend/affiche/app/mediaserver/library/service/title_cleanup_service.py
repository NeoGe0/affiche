import logging
from contextlib import contextmanager
from threading import Lock
from typing import Callable, Dict, List, NamedTuple, Optional

from sqlalchemy.orm import Session

from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.events import event_manager
from affiche.app.mediaserver.library.model import LibraryItemSearch
from affiche.app.mediaserver.library.service.item_rename_service import (
    ItemRenameError,
    ItemRenameService,
)
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository

logger = logging.getLogger(__name__)

PENDING = "pending"
RENAMED = "renamed"
FAILED = "failed"

class TitleProposal(NamedTuple):
    item_id: int
    current_title: str
    proposed_title: str
    provider: Optional[str]
    status: str = PENDING
    error: Optional[str] = None

class TitleCleanupReport(NamedTuple):
    approved: int = 0
    renamed: int = 0
    failed: int = 0

class TitleCleanupService:

    def __init__(self,
                 session_factory: Callable[[], Session],
                 rename_service_factory: Callable[[Session], ItemRenameService]):
        self._session_factory = session_factory
        self._rename_service_factory = rename_service_factory
        self._runs: Dict[int, Dict[int, TitleProposal]] = {}
        self._lock = Lock()

    def proposals(self, media_server_id: int, library_id: int) -> List[TitleProposal]:
        with self._session() as session:
            LibraryRepository(session).get_library(media_server_id, library_id)
            flagged = LibraryRepository(session).find_items(
                LibraryItemSearch(library_id=library_id, title_mismatched=True))

        run = self._run(library_id)
        finished = [row for row in run.values() if row.status != PENDING]
        pending = [
            TitleProposal(item_id=item.id, current_title=item.title,
                          proposed_title=item.catalogue_title, provider=item.catalogue_provider)
            for item in flagged
            if item.catalogue_title and run.get(item.id, TitleProposal(0, "", "", None)).status
            == PENDING
        ]
        return finished + sorted(pending, key=lambda row: row.current_title.casefold())

    def apply(self,
              media_server_id: int,
              library_id: int,
              item_ids: List[int],
              cancel_check: Callable[[], bool] = None) -> TitleCleanupReport:
        with self._session() as session:
            LibraryRepository(session).get_library(media_server_id, library_id)
            approved = LibraryRepository(session).find_items(LibraryItemSearch(
                library_id=library_id, title_mismatched=True, item_ids=item_ids))

        approved = [item for item in approved if item.catalogue_title]
        if not approved:
            return TitleCleanupReport()

        self._begin(library_id, approved)
        report = TitleCleanupReport(approved=len(approved))
        for index, item in enumerate(approved):
            if cancel_check and cancel_check():
                logger.info("[title-cleanup] cancelled after %d items", index)
                break
            report = self._apply_one(media_server_id, item, report)
            report_task_progress(index + 1, len(approved), "Titles")

        if report.renamed:
            event_manager.publish_library_synced(media_server_id, library_id)
        logger.info("[title-cleanup] library %s: %d approved, %d renamed, %d failed",
                    library_id, report.approved, report.renamed, report.failed)
        return report

    def renamed_item_ids(self, library_id: int) -> List[int]:
        return [row.item_id for row in self._run(library_id).values() if row.status == RENAMED]

    def _apply_one(self, media_server_id: int, item,
                   report: TitleCleanupReport) -> TitleCleanupReport:
        try:
            with self._session() as session:
                self._rename_service_factory(session).rename_item(
                    media_server_id, item.library_id, item.id, item.catalogue_title)
            self._record(item, RENAMED)
            logger.info("[title-cleanup] %s -> %s", item.title, item.catalogue_title)
            return report._replace(renamed=report.renamed + 1)
        except ItemRenameError as error:
            self._record(item, FAILED, error.message)
            logger.warning("[title-cleanup] %s: refused (%s)", item.title, error.message)
            return report._replace(failed=report.failed + 1)
        except Exception:
            self._record(item, FAILED, "Affiche could not complete this rename.")
            logger.exception("[title-cleanup] %s (%s): FAILED", item.id, item.title)
            return report._replace(failed=report.failed + 1)

    def _begin(self, library_id: int, approved: List) -> None:
        with self._lock:
            self._runs[library_id] = {
                item.id: TitleProposal(item_id=item.id, current_title=item.title,
                                       proposed_title=item.catalogue_title,
                                       provider=item.catalogue_provider)
                for item in approved
            }

    def _record(self, item, status: str, error: Optional[str] = None) -> None:
        with self._lock:
            run = self._runs.setdefault(item.library_id, {})
            row = run.get(item.id)
            run[item.id] = (row or TitleProposal(
                item_id=item.id, current_title=item.title,
                proposed_title=item.catalogue_title, provider=item.catalogue_provider,
            ))._replace(status=status, error=error)

    def _run(self, library_id: int) -> Dict[int, TitleProposal]:
        with self._lock:
            return dict(self._runs.get(library_id, {}))

    @contextmanager
    def _session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()
