from typing import Callable, Optional

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from affiche.app.asynch.async_task_service import AsyncTaskService
from affiche.app.auth.model.user import User, UserRole
from affiche.app.auth.service.auth_service import AuthService
from affiche.app.auth.service.user_repository import UserRepository
from affiche.app.dashboard import DashboardService
from affiche.app.mediaserver.service.collection_poster_service import CollectionPosterService
from affiche.app.provider_stats import ProviderStatsService
from affiche.app.search import SearchService
from affiche.app.task_history.service.task_history_service import TaskHistoryService
from affiche.app.events import internal_event_bus
from affiche.app.events.event_manager import event_manager
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.image import (PosterDecorationService, OverlayGenerator, ImageComposer,
                               TextRenderer, make_thumbnail)
from affiche.app.image.font_store import FontStore
from affiche.app.image.image_proxy import ImageProxyService
from affiche.app.mediaserver.service.media_server_connector_factory import MediaServerConnectorFactory
from affiche.app.mediaserver.service.media_server_probe_service import MediaServerProbeService
from affiche.app.mediaserver.library import LibraryService
from affiche.app.mediaserver.library.seasons.library_season_service import LibrarySeasonService
from affiche.app.mediaserver.library.episodes.library_episode_service import LibraryEpisodeService
from affiche.app.mediaserver.library.collections.library_collection_service import LibraryCollectionService
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.service.source_poster_service import SourcePosterService
from affiche.app.mediaserver.library.settings.library_settings_service import LibrarySettingsService
from affiche.app.notifications.service.notification_service import NotificationService
from affiche.app.style_profile.service.style_profile_service import StyleProfileService
from affiche.app.mediaserver.service.jellyfin_sync_service import JellyfinSynchronisationService
from affiche.app.mediaserver.service.plex_sync_service import PlexSynchronisationService
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository
from affiche.app.mediaserver.service.media_server_service import MediaServerService
from affiche.app.mediaserver.library.sync.media_server_synchronisation_service import MediaServerSynchronisationService
from affiche.app.service_configuration.provider_service import ProviderService
from affiche.app.service_configuration.service.configuration_repository import ConfigurationRepository
from affiche.app.service_configuration.service.service_configuration_service import ServiceConfigurationService
from affiche.config.database import get_db, SessionLocal
from affiche.config.env_config import FILESTORE_DIR
from affiche.config.poster_config_store import PosterConfigStore
from affiche.config.app_settings_store import AppSettingsStore
from affiche.external.poster.poster_service import PosterAggregatorService
from affiche.external.poster.poster_service_factory import PosterServiceFactory
from affiche.external.poster.provider.mediux import is_mediux_url, mediux_download_headers

def _mediux_download_headers(url: str) -> dict:
    if not is_mediux_url(url):
        return {}
    session = SessionLocal()
    try:
        config = ServiceConfigurationService(ConfigurationRepository(session)).get_config("mediux")
        token = config.token if (config and config.enabled and config.token) else None
    finally:
        session.close()
    return mediux_download_headers(url, token)

class ServiceContainer:

    def __init__(self):

        self._file_store: Optional[FileStoreService] = None
        self._async_task_service: Optional[AsyncTaskService] = None
        self._poster_decorator: Optional[PosterDecorationService] = None
        self._text_renderer: Optional[TextRenderer] = None
        self._poster_config_store: Optional[PosterConfigStore] = None
        self._app_settings_store: Optional[AppSettingsStore] = None
        self._connector_factory: Optional[MediaServerConnectorFactory] = None
        self._font_store: Optional[FontStore] = None
        self._collection_file_store: Optional[FileStoreService] = None

    @property
    def file_store(self) -> FileStoreService:
        if self._file_store is None:
            self._file_store = FileStoreService(root_dir=FILESTORE_DIR,
                                                thumbnailer=make_thumbnail)
        return self._file_store

    @property
    def collection_file_store(self) -> FileStoreService:
        if self._collection_file_store is None:
            self._collection_file_store = FileStoreService(root_dir=FILESTORE_DIR,
                                                           thumbnailer=make_thumbnail,
                                                           kind="collections")
        return self._collection_file_store

    @property
    def async_task_service(self) -> AsyncTaskService:
        if self._async_task_service is None:
            from affiche.app.task_history import make_task_recorder
            from affiche.config.database import SessionLocal
            self._async_task_service = AsyncTaskService(
                max_tasks=100, history=make_task_recorder(SessionLocal))
        return self._async_task_service

    @property
    def text_renderer(self) -> TextRenderer:
        if self._text_renderer is None:
            self._text_renderer = TextRenderer()
        return self._text_renderer

    @property
    def poster_config_store(self) -> PosterConfigStore:
        if self._poster_config_store is None:
            self._poster_config_store = PosterConfigStore()
        return self._poster_config_store

    @property
    def app_settings_store(self) -> AppSettingsStore:
        if self._app_settings_store is None:
            self._app_settings_store = AppSettingsStore()
        return self._app_settings_store

    @property
    def poster_decorator(self) -> PosterDecorationService:
        if self._poster_decorator is None:
            overlay_options, text_options, generation_options = self.poster_config_store.get()
            self._poster_decorator = PosterDecorationService(
                options=overlay_options,
                text_options=text_options,
                generator=OverlayGenerator(),
                composer=ImageComposer(auth_headers_resolver=_mediux_download_headers),
                text_renderer=self.text_renderer,
                jpeg_quality=generation_options.jpeg_quality
            )
        return self._poster_decorator

    def reset_poster_decorator(self) -> None:
        self._poster_decorator = None

    @property
    def font_store(self) -> FontStore:
        if self._font_store is None:
            self._font_store = FontStore()
        return self._font_store

    @property
    def connector_factory(self) -> MediaServerConnectorFactory:
        if self._connector_factory is None:
            self._connector_factory = MediaServerConnectorFactory(
                session_factory=SessionLocal
            )
            for event in ("media_server.updated", "media_server.deleted"):
                internal_event_bus.subscribe(
                    event,
                    lambda media_server_id: self._connector_factory.invalidate(media_server_id)
                )
        return self._connector_factory

    def plex_synchronisation_service(self,
                                     session: Session):
        return PlexSynchronisationService(self.library_service(session),
                                          self.library_settings_service(session),
                                          self.library_season_service(session),
                                          self.library_episode_service(session),
                                          self.library_collection_service(session),
                                          self.file_store,
                                          self.connector_factory)

    def jellyfin_synchronisation_service(self,
                                         session: Session):
        return JellyfinSynchronisationService(self.library_service(session),
                                              self.library_settings_service(session),
                                              self.library_season_service(session),
                                              self.library_episode_service(session),
                                              self.library_collection_service(session),
                                              self.file_store,
                                              self.connector_factory)

    def media_server_synchronisation_service(self,
                                             session: Session):
        return MediaServerSynchronisationService(
            session,
            self.media_server_service(session),
            self.plex_synchronisation_service(session),
            self.jellyfin_synchronisation_service(session)
        )

    def auth_service(self, session: Session) -> AuthService:
        return AuthService(UserRepository(session))

    def configuration_repo(self, session: Session) -> ConfigurationRepository:
        return ConfigurationRepository(session)

    def service_configuration_service(self, session: Session) -> ServiceConfigurationService:
        return ServiceConfigurationService(self.configuration_repo(session))

    def media_server_repo(self, session: Session) -> MediaServerRepository:
        return MediaServerRepository(session)

    def media_server_service(self, session: Session) -> MediaServerService:
        return MediaServerService(session,
                                  self.media_server_repo(session),
                                  self.library_service(session),
                                  self.connector_factory)

    def library_settings_service(self, session: Session) -> LibrarySettingsService:
        return LibrarySettingsService(session)
    def library_season_service(self, session: Session) -> LibrarySeasonService:
        return LibrarySeasonService(session)

    def library_episode_service(self, session: Session) -> LibraryEpisodeService:
        return LibraryEpisodeService(session)

    def library_collection_service(self, session: Session) -> LibraryCollectionService:
        return LibraryCollectionService(session, self.connector_factory)

    def library_service(self, session: Session) -> LibraryService:
        return LibraryService(session, self.file_store, self.app_settings_store)

    def dashboard_service(self, session: Session) -> DashboardService:
        return DashboardService(session)

    def search_service(self, session: Session) -> SearchService:
        return SearchService(session)

    def task_history_service(self, session: Session) -> TaskHistoryService:
        return TaskHistoryService(session)

    def provider_stats_service(self, session: Session) -> ProviderStatsService:
        return ProviderStatsService(session)

    def poster_factory(self, session: Session) -> PosterServiceFactory:
        config_service = self.service_configuration_service(session)
        return PosterServiceFactory(config_service)

    def poster_aggregator(self, session: Session) -> PosterAggregatorService:
        factory = self.poster_factory(session)
        return PosterAggregatorService(factory.get_configured_services())

    def poster_sync_service(
            self,
            session_factory: Callable[[], Session] = None
    ) -> LibraryPosterService:
        if session_factory is None:
            session_factory = SessionLocal

        session = session_factory()
        try:
            poster_aggregator = self.poster_aggregator(session)
        finally:
            session.close()

        return LibraryPosterService(
            session_factory=session_factory,
            poster_aggregator=poster_aggregator,
            file_store=self.file_store,
            decorator=self.poster_decorator,
            connector_factory=self.connector_factory,
        )

    def source_poster_service(
            self,
            session_factory: Callable[[], Session] = None
    ) -> SourcePosterService:
        return SourcePosterService(
            session_factory=session_factory or SessionLocal,
            file_store=self.file_store,
        )

    def collection_poster_service(
            self,
            session_factory: Callable[[], Session] = None
    ) -> CollectionPosterService:
        return CollectionPosterService(
            session_factory=session_factory or SessionLocal,
            file_store=self.collection_file_store,
            decorator=self.poster_decorator,
            aggregator_factory=self.poster_aggregator,
            connector_factory=self.connector_factory,
        )

container = ServiceContainer()

event_manager.set_poster_version_resolver(
    lambda library_id, item_id, season_number: container.file_store.version(
        library_id, item_id, season_number=season_number
    )
)

def get_provider_service() -> ProviderService:
    return ProviderService()

def get_media_server_probe_service() -> MediaServerProbeService:
    return MediaServerProbeService()

def get_async_task_service() -> AsyncTaskService:
    return container.async_task_service

def get_file_store_service() -> FileStoreService:
    return container.file_store

def get_poster_decoration_service() -> PosterDecorationService:
    return container.poster_decorator

def get_text_renderer() -> TextRenderer:
    return container.text_renderer

def get_font_store() -> FontStore:
    return container.font_store

def get_poster_config_store() -> PosterConfigStore:
    return container.poster_config_store

def get_app_settings_store() -> AppSettingsStore:
    return container.app_settings_store

def reset_poster_decorator() -> None:
    container.reset_poster_decorator()

def get_service_configuration_service(
        session: Session = Depends(get_db)
) -> ServiceConfigurationService:
    return container.service_configuration_service(session)

def get_image_proxy_service(
        config_service: ServiceConfigurationService = Depends(get_service_configuration_service)
) -> ImageProxyService:
    return ImageProxyService(config_service)

def get_media_server_synchronisation_service(
        session: Session = Depends(get_db)
) -> MediaServerSynchronisationService:
    return container.media_server_synchronisation_service(session)

def get_media_server_service(
        session: Session = Depends(get_db)
) -> MediaServerService:
    return container.media_server_service(session)

def get_library_settings_service(
        session: Session = Depends(get_db)
) -> LibrarySettingsService:
    return container.library_settings_service(session)

def get_style_profile_service(
        session: Session = Depends(get_db)
) -> StyleProfileService:
    return StyleProfileService(session)

def get_notification_service(
        session: Session = Depends(get_db)
) -> NotificationService:
    return NotificationService(session)

def get_library_service(
        session: Session = Depends(get_db)
) -> LibraryService:
    return container.library_service(session)

def get_library_collection_service(
        session: Session = Depends(get_db)
) -> LibraryCollectionService:
    return container.library_collection_service(session)

def get_dashboard_service(
        session: Session = Depends(get_db)
) -> DashboardService:
    return container.dashboard_service(session)

def get_search_service(
        session: Session = Depends(get_db)
) -> SearchService:
    return container.search_service(session)

def get_task_history_service(
        session: Session = Depends(get_db)
) -> TaskHistoryService:
    return container.task_history_service(session)

def get_provider_stats_service(
        session: Session = Depends(get_db)
) -> ProviderStatsService:
    return container.provider_stats_service(session)

def get_poster_factory(
        session: Session = Depends(get_db)
) -> PosterServiceFactory:
    return container.poster_factory(session)

def get_poster_aggregator(
        session: Session = Depends(get_db)
) -> PosterAggregatorService:
    return container.poster_aggregator(session)

def get_poster_sync_service() -> LibraryPosterService:
    return container.poster_sync_service()

def get_auth_service(
        session: Session = Depends(get_db)
) -> AuthService:
    return container.auth_service(session)

def get_current_user(
        affiche_session: Optional[str] = Cookie(default=None),
        service: AuthService = Depends(get_auth_service),
) -> User:
    user = service.user_from_token(affiche_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user.password_temporary:
        raise HTTPException(status_code=403, detail="Password change required")
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user
