import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Callable, List, NamedTuple

from sqlalchemy.orm import Session

from affiche.app.asynch.async_task_service import report_task_progress
from affiche.app.events import event_manager
from affiche.app.filestore.filestore import FileStoreService, poster_digest
from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.image.model.text_options import TextOptions
from affiche.app.image.poster_decorator_service import PosterDecorationService
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.provider_stats import ProviderStatsService
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.mediaserver.service.media_server_connector_factory import MediaServerConnectorFactory
from affiche.app.mediaserver.service.media_server_connector_protocol import MediaServerConnector
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository
from affiche.app.mediaserver.service.item_selection import resolve_selection
from affiche.app.mediaserver.service.library_session import library_session
from affiche.app.mediaserver.service.library_style import (
    GLOBAL_STYLE,
    LibraryPosterStyle,
    resolve_library_style,
)
from affiche.app.mediaserver.service.poster_resolver import PosterResolver, ServerPosterSettings
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
from affiche.app.mediaserver.service.poster_uploader import PosterUploader
from affiche.app.mediaserver.service.poster_workers import MAX_WORKERS
from affiche.app.style_profile.service.style_profile_repository import StyleProfileRepository
from affiche.config.exceptions.exceptions import LibraryDisabledException
from affiche.config.language_config import normalize_language_order
from affiche.config.library_config import DEFAULT_PROVIDER_ORDER
from affiche.external.poster.poster_service import PosterAggregatorService

from affiche.app.mediaserver.library.model import LibraryItemSearch, SeasonPosterState

logger = logging.getLogger(__name__)

MAX_ERROR_LENGTH = 1000

MANUAL_PROVIDER = "manual"

def _error_text(error: Exception) -> str:
    return str(error).strip() or error.__class__.__name__

def _season_failure_message(failed_seasons: List[int]) -> str:
    numbers = ", ".join(str(n) for n in sorted(failed_seasons))
    return f"Season poster generation failed for season(s): {numbers}"

class StoredPoster(NamedTuple):
    path: str
    digest: str

class StyleStaleness(NamedTuple):
    stale: int
    total: int

class LibraryPosterService:

    def __init__(
            self,
            session_factory: Callable[[], Session],
            poster_aggregator: PosterAggregatorService,
            file_store: FileStoreService,
            decorator: PosterDecorationService,
            connector_factory: MediaServerConnectorFactory,
    ):
        self._session_factory = session_factory
        self._file_store = file_store
        self._resolver = PosterResolver(poster_aggregator, file_store)
        self._uploader = PosterUploader(file_store, session_factory)
        self._resetter = PosterResetter(file_store, session_factory)
        self._decorator = decorator
        self._connector_factory = connector_factory

    def reset_item_posters(self,
                           media_server_id: int,
                           library_id: int,
                           item_id: int):
        with library_session(self._session_factory) as (repo, session):
            item = repo.get_library_item(library_id, item_id)
            connector = self._get_connector(media_server_id)
            self._resetter.reset_poster(repo, item, connector)
            if item.type == 'show':
                season_service = LibrarySeasonService(session)
                self._resetter.reset_season_posters(season_service, item, connector)

    def reset_libraries_posters(self,
                                media_server_id: int,
                                library_id: int = None,
                                cancel_check: Callable[[], bool] = None,
                                include_unprocessed: bool = False):
        with library_session(self._session_factory) as (repo, _):
            if library_id:
                logger.info("Starting poster reset for library %d (include_unprocessed=%s)",
                            library_id, include_unprocessed)
                self._resetter.reset_library_posters(
                media_server_id, library_id, self._get_connector(media_server_id),
                cancel_check, include_unprocessed)
            else:
                logger.info("Starting poster reset for all libraries (include_unprocessed=%s)",
                            include_unprocessed)
                libraries = repo.find_libraries(LibrarySearch(media_server_id=media_server_id, enabled=True))
                logger.info("Found %d enabled libraries", len(libraries))
                for library in libraries:
                    if cancel_check and cancel_check():
                        logger.info("Poster reset cancelled")
                        return
                    self._resetter.reset_library_posters(
                        media_server_id, library.id, self._get_connector(media_server_id),
                        cancel_check, include_unprocessed)

            logger.info("Poster reset completed")

    def apply_item_posters(self,
                           media_server_id: int,
                           library_id: int,
                           item_id: int,
                           upload: Optional[bool] = None):
        with library_session(self._session_factory) as (repo, session):
            library = repo.get_library(media_server_id, library_id)
            item = repo.get_library_item(library_id, item_id)
            provider_order = self._get_provider_order(session, library_id)
            settings = self._get_server_poster_settings(media_server_id)
            style = self._get_library_style(session, library_id)
            upload_enabled = upload if upload is not None else self._get_upload_enabled(session, library_id)
            connector = self._get_connector(media_server_id)

            try:
                poster = self._resolver.resolve_item_poster(item, self._get_media_type(library.type),
                                                   provider_order, settings)
                if not poster:
                    self._mark_item_failed(repo, item, "No poster found from any provider")
                    return
                if not self._process_item_poster(repo, session, item, poster.source, connector,
                                                 upload_enabled,
                                                 overlay_options=style.overlay_options,
                                                 text_options=style.text_options,
                                                 apply_style=poster.styled, provider=poster.provider):
                    self._mark_item_failed(repo, item, "Poster generation failed")
                    return

                if item.type == 'show':
                    season_service = LibrarySeasonService(session)
                    failed_seasons = self._process_series_seasons(
                        season_service, session, item, provider_order, settings, style, connector, upload_enabled)
                    if failed_seasons:
                        item.processed = False
                        self._mark_item_failed(repo, item, _season_failure_message(failed_seasons))
                        event_manager.publish_item_processed(item.library_id, item.id, processed=False)
            except Exception as error:
                logger.exception("Error applying posters for item %s", item.id)
                self._mark_item_failed(repo, item, _error_text(error))

    def apply_posters_to_library(self,
                                 media_server_id: int,
                                 library_id: int,
                                 cancel_check: Callable[[], bool] = None,
                                 upload: Optional[bool] = None):
        with library_session(self._session_factory) as (repo, _):
            logger.info("Starting poster sync for library %d", library_id)
            library = repo.get_library(media_server_id, library_id)
            if not library.enabled:
                raise LibraryDisabledException(library_id)

        self._process_library(media_server_id, library, cancel_check, upload=upload)
        logger.info("Poster sync completed")

    def apply_posters_to_all_libraries(self,
                                       media_server_id: int,
                                       cancel_check: Callable[[], bool] = None,
                                       upload: Optional[bool] = None):
        with library_session(self._session_factory) as (repo, _):
            logger.info("Starting poster sync for all libraries")
            libraries = repo.find_libraries(LibrarySearch(media_server_id=media_server_id, enabled=True))
            logger.info("Found %d enabled libraries", len(libraries))

        for library in libraries:
            if cancel_check and cancel_check():
                logger.info("Poster sync cancelled")
                return
            self._process_library(media_server_id, library, cancel_check, upload=upload)

        logger.info("Poster sync completed")

    def apply_posters_to_items(self,
                               media_server_id: int,
                               item_ids: List[int],
                               cancel_check: Callable[[], bool] = None,
                               upload: Optional[bool] = None):
        with library_session(self._session_factory) as (repo, _):
            selection = resolve_selection(repo, media_server_id, item_ids)

        total = sum(len(items) for _, items in selection)
        logger.info("Generating posters for %d selected item(s) across %d librar(ies)",
                    total, len(selection))
        for library, items in selection:
            if cancel_check and cancel_check():
                logger.info("Selection poster generation cancelled")
                return
            self._process_items(media_server_id, library, items, cancel_check, upload)

    def reset_items_posters(self,
                            media_server_id: int,
                            item_ids: List[int],
                            cancel_check: Callable[[], bool] = None):
        with library_session(self._session_factory) as (repo, _):
            selection = resolve_selection(repo, media_server_id, item_ids)

        connector = self._get_connector(media_server_id)
        for library, items in selection:
            if cancel_check and cancel_check():
                logger.info("Selection poster reset cancelled")
                return
            self._resetter.reset_items(items, library.name, connector, cancel_check,
                                       include_unprocessed=True)

    def upload_items_posters(self,
                             media_server_id: int,
                             item_ids: List[int],
                             cancel_check: Callable[[], bool] = None):
        with library_session(self._session_factory) as (repo, _):
            selection = resolve_selection(repo, media_server_id, item_ids)

        connector = self._get_connector(media_server_id)
        for library, items in selection:
            if cancel_check and cancel_check():
                logger.info("Selection poster upload cancelled")
                return
            self._uploader.upload_items(items, library.name, connector, cancel_check)

    def apply_poster(self,
                     media_server_id: int,
                     library_id: int,
                     item_id: int,
                     poster_url: str,
                     season_number: Optional[int] = None,
                     jpeg_quality: Optional[int] = None,
                     title: Optional[str] = None,
                     overlay_options: Optional[OverlayOptions] = None,
                     text_options: Optional[TextOptions] = None,
                     upload: Optional[bool] = None) -> bool:
        with library_session(self._session_factory) as (repo, session):
            item = repo.get_library_item(library_id, item_id)

            upload_enabled = upload if upload is not None else self._get_upload_enabled(session, library_id)
            connector = self._get_connector(media_server_id)

            style = self._get_library_style(session, library_id)
            overlay_options = overlay_options if overlay_options is not None else style.overlay_options
            text_options = text_options if text_options is not None else style.text_options

            if season_number is not None:
                season_service = LibrarySeasonService(session)
                return self._apply_season_poster(season_service, session, item, poster_url,
                                                 season_number, connector,
                                                 upload_enabled, jpeg_quality=jpeg_quality, title=title,
                                                 overlay_options=overlay_options, text_options=text_options)
            else:
                return self._process_item_poster(repo, session, item, poster_url, connector,
                                                 upload_enabled,
                                                 jpeg_quality=jpeg_quality, title=title,
                                                 overlay_options=overlay_options, text_options=text_options)

    def upload_item_poster(self,
                           media_server_id: int,
                           library_id: int,
                           item_id: int) -> bool:
        with library_session(self._session_factory) as (repo, session):
            item = repo.get_library_item(library_id, item_id)
            connector = self._get_connector(media_server_id)
            uploaded = self._uploader.upload_existing_item_poster(item, connector)
            if item.type == 'show':
                season_service = LibrarySeasonService(session)
                self._uploader.upload_existing_season_posters(season_service, item, connector)
            return uploaded

    def upload_libraries_posters(self,
                                 media_server_id: int,
                                 library_id: int = None,
                                 cancel_check: Callable[[], bool] = None):
        with library_session(self._session_factory) as (repo, _):
            if library_id:
                libraries = [repo.get_library(media_server_id, library_id)]
            else:
                libraries = repo.find_libraries(LibrarySearch(media_server_id=media_server_id, enabled=True))
                logger.info("Starting poster upload for %d enabled libraries", len(libraries))

        for library in libraries:
            if cancel_check and cancel_check():
                logger.info("Poster upload cancelled")
                return
            self._uploader.upload_library_posters(
                library, self._get_connector(media_server_id), cancel_check)

        logger.info("Poster upload completed")

    def _process_library(self,
                         media_server_id: int,
                         library: Library,
                         cancel_check: Callable[[], bool] = None,
                         upload: Optional[bool] = None):
        with library_session(self._session_factory) as (repo, _):
            items = repo.find_items(LibraryItemSearch(library_id=library.id, processed=False,
                                                      locked=False))
        self._process_items(media_server_id, library, items, cancel_check=cancel_check, upload=upload)

    def _process_items(self,
                       media_server_id: int,
                       library: Library,
                       items: List[LibraryItem],
                       cancel_check: Callable[[], bool] = None,
                       upload: Optional[bool] = None):
        library_id = library.id
        library_type = library.type
        library_name = library.name

        with library_session(self._session_factory) as (_, session):
            upload_enabled = upload if upload is not None else self._get_upload_enabled(session, library_id)
            provider_order = self._get_provider_order(session, library_id)
            style = self._get_library_style(session, library_id)

        media_type = self._get_media_type(library_type)
        settings = self._get_server_poster_settings(media_server_id)
        connector = self._get_connector(media_server_id)

        total = len(items)
        progress_label = f"Generating posters — {library_name}"
        report_task_progress(0, total, progress_label)

        processed = 0
        failed = 0
        cancelled = False

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_item = {
                executor.submit(
                    self._process_item,
                    item,
                    media_type,
                    library_type,
                    provider_order,
                    settings,
                    style,
                    connector,
                    upload_enabled,
                    cancel_check
                ): item
                for item in items
            }

            for future in as_completed(future_to_item):
                if cancel_check and cancel_check():
                    logger.info("Processing cancelled for library '%s', shutting down", library_name)
                    executor.shutdown(wait=False, cancel_futures=True)
                    cancelled = True
                    break

                item = future_to_item[future]
                try:
                    if future.result():
                        processed += 1
                        logger.info("[generation] item %s (%s): SUCCESS", item.id, item.title)
                    else:
                        failed += 1
                        logger.warning("[generation] item %s (%s): FAILED", item.id, item.title)
                except Exception:
                    logger.exception("[generation] item %s (%s): FAILED (exception)", item.id, item.title)
                    failed += 1
                report_task_progress(processed + failed, total, progress_label)

        if cancelled:
            logger.info("Library '%s' cancelled: %d processed before cancellation", library_name, processed)
        else:
            logger.info("Library '%s' complete: %d processed, %d failed", library_name, processed, failed)

    def _process_item(self,
                      item: LibraryItem,
                      media_type: str,
                      library_type: str,
                      provider_order: List[str],
                      settings: ServerPosterSettings,
                      style: LibraryPosterStyle,
                      connector: MediaServerConnector,
                      upload: bool,
                      cancel_check: Callable[[], bool] = None) -> bool:
        if cancel_check and cancel_check():
            return False

        with library_session(self._session_factory) as (repo, session):
            try:
                poster = self._resolver.resolve_item_poster(item, media_type, provider_order, settings)

                if not poster:
                    logger.info("[generation] item %s (%s): no poster URL found from any provider",
                                item.id, item.title)
                    self._mark_item_failed(repo, item, "No poster found from any provider")
                    return False

                if not self._process_item_poster(repo, session, item, poster.source, connector,
                                                 upload,
                                                 overlay_options=style.overlay_options,
                                                 text_options=style.text_options,
                                                 apply_style=poster.styled, provider=poster.provider):
                    self._mark_item_failed(repo, item, "Poster generation failed")
                    return False

                if library_type == "show":
                    season_service = LibrarySeasonService(session)
                    failed_seasons = self._process_series_seasons(
                        season_service, session, item, provider_order, settings, style, connector, upload)
                    if failed_seasons:
                        item.processed = False
                        self._mark_item_failed(repo, item, _season_failure_message(failed_seasons))
                        event_manager.publish_item_processed(item.library_id, item.id, processed=False)
                        return False

                return True
            except Exception as error:
                logger.exception("Error processing item %s", item.id)
                self._mark_item_failed(repo, item, _error_text(error))
                return False

    def _mark_item_failed(self, repo: LibraryRepository, item: LibraryItem, message: str):
        item.error_message = (message or "Unknown error")[:MAX_ERROR_LENGTH]
        repo.create_or_update_item(item)

    def _process_item_poster(self,
                             repo: LibraryRepository,
                             session: Session,
                             item: LibraryItem,
                             poster_url: str,
                             connector: MediaServerConnector,
                             upload: bool,
                             jpeg_quality: Optional[int] = None,
                             title: Optional[str] = None,
                             overlay_options: Optional[OverlayOptions] = None,
                             text_options: Optional[TextOptions] = None,
                             apply_style: bool = True,
                             provider: str = MANUAL_PROVIDER) -> bool:
        stored = self._save_item_poster(item, poster_url, jpeg_quality=jpeg_quality, title=title,
                                        overlay_options=overlay_options, text_options=text_options,
                                        apply_style=apply_style)
        if not stored:
            return False

        uploaded = upload and self._uploader.upload_if_changed(item, stored.path, stored.digest, connector)

        item.processed = True
        item.poster_provider = provider
        item.style_hash = self._decorator.style_fingerprint(overlay_options, text_options, apply_style)
        if not uploaded:
            item.poster_uploaded_at = None
        item.error_message = None
        ProviderStatsService(session).record(provider, item.library_id)
        repo.create_or_update_item(item)
        event_manager.publish_item_processed(item.library_id, item.id)
        return True

    def _save_item_poster(self,
                          item: LibraryItem,
                          poster_url: str,
                          jpeg_quality: Optional[int] = None,
                          title: Optional[str] = None,
                          overlay_options: Optional[OverlayOptions] = None,
                          text_options: Optional[TextOptions] = None,
                          apply_style: bool = True) -> Optional[StoredPoster]:
        poster_bytes = self._decorator.decorate_poster(poster_url, title or item.title,
                                                       jpeg_quality=jpeg_quality,
                                                       overlay_options=overlay_options,
                                                       text_options=text_options,
                                                       apply_style=apply_style)
        if not poster_bytes:
            return None

        self._preserve_source(item)
        poster_path = self._file_store.save(item.library_id, item.id, poster_bytes)
        return StoredPoster(str(poster_path), poster_digest(poster_bytes))

    def _preserve_source(self, item: LibraryItem, season: Optional[LibrarySeason] = None):
        target = season or item
        if target.processed:
            return
        season_number = season.season_number if season else None
        self._file_store.preserve_source(item.library_id, item.id, season_number=season_number)

    def _process_series_seasons(self,
                                season_service: LibrarySeasonService,
                                session: Session,
                                item: LibraryItem,
                                provider_order: List[str],
                                settings: ServerPosterSettings,
                                style: LibraryPosterStyle,
                                connector: MediaServerConnector,
                                upload: bool) -> List[int]:
        seasons = season_service.get_item_seasons(item.library_id, item.id, processed=False)
        failed_seasons: List[int] = []
        for season in seasons:
            try:
                if not self._process_season(season_service, session, season, item, provider_order,
                                            settings, style, connector, upload):
                    failed_seasons.append(season.season_number)
            except Exception:
                logger.exception("Failed to process season %d for '%s'", season.season_number, item.title)
                failed_seasons.append(season.season_number)
        return failed_seasons

    def _process_season(self,
                        season_service: LibrarySeasonService,
                        session: Session,
                        season: LibrarySeason,
                        item: LibraryItem,
                        provider_order: List[str],
                        settings: ServerPosterSettings,
                        style: LibraryPosterStyle,
                        connector: MediaServerConnector,
                        upload: bool) -> bool:
        poster = self._resolver.resolve_season_poster(item, season, provider_order, settings)

        if not poster:
            logger.info("[generation] season %d of '%s': no poster URL found from any provider",
                        season.season_number, item.title)
            return False

        if self._process_season_poster(season_service, session, season, item, poster.source,
                                       connector,
                                       upload, overlay_options=style.overlay_options,
                                       text_options=style.text_options,
                                       apply_style=poster.styled, provider=poster.provider):
            logger.info("[generation] season %d of '%s': SUCCESS", season.season_number, item.title)
            return True

        logger.warning("[generation] season %d of '%s': FAILED", season.season_number, item.title)
        return False

    def _save_season_poster(self,
                            season: LibrarySeason,
                            item: LibraryItem,
                            poster_url: str,
                            jpeg_quality: Optional[int] = None,
                            title: Optional[str] = None,
                            overlay_options: Optional[OverlayOptions] = None,
                            text_options: Optional[TextOptions] = None,
                            apply_style: bool = True) -> Optional[StoredPoster]:
        poster_bytes = self._decorator.decorate_poster(poster_url,
                                                       title or ("Season %d" % season.season_number),
                                                       jpeg_quality=jpeg_quality,
                                                       overlay_options=overlay_options,
                                                       text_options=text_options,
                                                       apply_style=apply_style)
        if not poster_bytes:
            return None

        self._preserve_source(item, season=season)
        poster_path = self._file_store.save(
            item.library_id,
            item.id,
            poster_bytes,
            season_number=season.season_number
        )
        return StoredPoster(str(poster_path), poster_digest(poster_bytes))

    def _process_season_poster(self,
                               season_service: LibrarySeasonService,
                               session: Session,
                               season: LibrarySeason,
                               item: LibraryItem,
                               poster_url: str,
                               connector: MediaServerConnector,
                               upload: bool,
                               jpeg_quality: Optional[int] = None,
                               title: Optional[str] = None,
                               overlay_options: Optional[OverlayOptions] = None,
                               text_options: Optional[TextOptions] = None,
                               apply_style: bool = True,
                               provider: str = MANUAL_PROVIDER) -> bool:
        stored = self._save_season_poster(season, item, poster_url, jpeg_quality=jpeg_quality,
                                          title=title, overlay_options=overlay_options,
                                          text_options=text_options, apply_style=apply_style)
        if not stored:
            return False

        if upload:
            self._uploader.upload_season_if_changed(season_service, season, item, stored.path, stored.digest,
                                           connector)

        ProviderStatsService(session).record(provider, item.library_id)
        season_service.update_seasons([season], SeasonPosterState(
            poster_provider=provider,
            style_hash=self._decorator.style_fingerprint(overlay_options, text_options, apply_style),
            processed=True,
        ))
        event_manager.publish_season_processed(item.library_id, item.id, season.season_number)
        return True

    def _apply_season_poster(self,
                             season_service: LibrarySeasonService,
                             session: Session,
                             item: LibraryItem,
                             poster_url: str,
                             season_number: int,
                             connector: MediaServerConnector,
                             upload: bool,
                             jpeg_quality: Optional[int] = None,
                             title: Optional[str] = None,
                             overlay_options: Optional[OverlayOptions] = None,
                             text_options: Optional[TextOptions] = None) -> bool:
        seasons = season_service.get_item_seasons(item.library_id, item.id)
        season = next((s for s in seasons if s.season_number == season_number), None)
        if not season:
            logger.error("Season %d not found for item %s", season_number, item.title)
            return False

        return self._process_season_poster(season_service, session, season, item, poster_url,
                                           connector, upload,
                                            jpeg_quality=jpeg_quality, title=title,
                                            overlay_options=overlay_options, text_options=text_options)

    def get_style_staleness(self, library_id: int) -> StyleStaleness:
        with library_session(self._session_factory) as (repo, session):
            style = self._get_library_style(session, library_id)
            current_hash = self._decorator.style_fingerprint(style.overlay_options,
                                                             style.text_options)
            stale, total = repo.count_style_staleness(
                LibraryItemSearch(library_id=library_id, processed=True), current_hash)
            return StyleStaleness(stale=stale, total=total)

    def _get_media_type(self, library_type: str) -> str:
        return "movie" if library_type == "movie" else "show"

    def _get_library_settings(self, session: Session, library_id: int):
        settings_service = LibrarySettingsService(session)
        return settings_service.get_settings(library_id)

    def _get_provider_order(self,
                            session: Session,
                            library_id: int) -> List[str]:
        settings = self._get_library_settings(session, library_id)
        if settings and settings.provider_order:
            return settings.provider_order
        return DEFAULT_PROVIDER_ORDER

    def _get_server_poster_settings(self, media_server_id: int) -> ServerPosterSettings:
        with library_session(self._session_factory) as (_, session):
            media_server = MediaServerRepository(session).get(media_server_id)
            return ServerPosterSettings(
                language_order=normalize_language_order(media_server.language_order),
                fallback_to_server_poster=media_server.fallback_to_server_poster,
                skip_style_when_not_textless=media_server.skip_style_when_not_textless,
            )

    @staticmethod
    def _get_library_style(session: Session, library_id: int) -> LibraryPosterStyle:
        return resolve_library_style(session, library_id)

    def _get_upload_enabled(self,
                            session: Session,
                            library_id: int) -> bool:
        settings = self._get_library_settings(session, library_id)
        if settings:
            return settings.upload_enabled
        return True

    def _get_connector(self, media_server_id: int) -> MediaServerConnector:
        return self._connector_factory.get(media_server_id)
