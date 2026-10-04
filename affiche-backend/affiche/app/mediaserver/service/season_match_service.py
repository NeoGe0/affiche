import logging
from contextlib import contextmanager
from typing import Callable, List, NamedTuple, Optional

from sqlalchemy.orm import Session

from affiche.app.events import event_manager
from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.mediaserver.library.model import LibraryItemSearch
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.external.poster import season_match

logger = logging.getLogger(__name__)

class SeasonMatchReport(NamedTuple):
    shows_scanned: int = 0
    shows_suspect: int = 0
    resolved: int = 0
    unresolved: int = 0

class SeasonMatchService:

    def __init__(self,
                 session_factory: Callable[[], Session],
                 aggregator_factory: Callable[[Session], object]):
        self._session_factory = session_factory
        self._aggregator_factory = aggregator_factory

    def fix_library_season_matches(self,
                                   media_server_id: int,
                                   library_id: int,
                                   cancel_check: Callable[[], bool] = None) -> SeasonMatchReport:
        with self._session() as session:
            aggregator = self._aggregator_factory(session)
            shows = [item for item in LibraryRepository(session).find_items(
                LibraryItemSearch(library_id=library_id)) if item.type != "movie"]

        if not shows:
            return SeasonMatchReport()

        logger.info("[season-match] scanning %d shows in library %s", len(shows), library_id)
        report = SeasonMatchReport(shows_scanned=len(shows))
        for index, show in enumerate(shows):
            if cancel_check and cancel_check():
                logger.info("[season-match] cancelled after %d shows", index)
                break
            report = self._sweep_show(show, aggregator, report)
            report_task_progress(index + 1, len(shows), "Season matches")

        if report.resolved:
            event_manager.publish_library_synced(media_server_id, library_id)
        logger.info("[season-match] library %s: %d suspect, %d resolved, %d left for review",
                    library_id, report.shows_suspect, report.resolved, report.unresolved)
        return report

    def _sweep_show(self, show, aggregator, report: SeasonMatchReport) -> SeasonMatchReport:
        try:
            seasons = self._seasons_needing_a_match(show, aggregator)
            if not seasons:
                return report

            resolved = sum(self._resolve_one(show, season, aggregator) for season in seasons)
            return report._replace(
                shows_suspect=report.shows_suspect + 1,
                resolved=report.resolved + resolved,
                unresolved=report.unresolved + len(seasons) - resolved,
            )
        except Exception:
            logger.exception("[season-match] %s (%s): FAILED", show.id, show.title)
            return report

    def _seasons_needing_a_match(self, show, aggregator) -> List:
        if not show.tmdb_id or not show.tvdb_id:
            return []

        with self._session() as session:
            stored = LibrarySeasonService(session).get_item_seasons(show.library_id, show.id)

        pending = [s for s in stored if s.tmdb_id_override is None and s.season_number != 0]
        if not pending:
            return []

        facts = aggregator.describe_tmdb_series(int(show.tmdb_id))
        missing = set(season_match.missing_seasons(facts, [s.season_number for s in pending]))
        return [s for s in pending if s.season_number in missing]

    def _resolve_one(self, show, season, aggregator) -> bool:
        suggestion = aggregator.suggest_season_match(
            show_title=show.title,
            season_number=season.season_number,
            tvdb_id=int(show.tvdb_id),
        )
        if suggestion is None:
            logger.info("[season-match] %s S%d: no confident match, left for review",
                        show.title, season.season_number)
            return False

        with self._session() as session:
            LibrarySeasonService(session).set_tmdb_match(
                season.id, suggestion.tmdb_id, suggestion.season_number)
        logger.info("[season-match] %s S%d -> TMDB %d S%d (%s)", show.title, season.season_number,
                    suggestion.tmdb_id, suggestion.season_number, suggestion.series_name)
        return True

    @contextmanager
    def _session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()
