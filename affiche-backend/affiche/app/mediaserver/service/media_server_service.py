import secrets
from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.events import internal_event_bus
from affiche.app.mediaserver.library import LibraryService
from affiche.app.mediaserver.library.model import Library, LibrarySearch
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerLibrary
from affiche.app.mediaserver.service.media_server_connector_factory import MediaServerConnectorFactory
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository
from affiche.app.service_configuration.exceptions import (MediaServerNotFoundError,
                                                          MediaServerUnreachableError)
from affiche.config.app_settings_store import AppSettingsStore
from affiche.config.language_config import normalize_language_order

class MediaServerService:

    def __init__(self,
                 session: Session,
                 repository: MediaServerRepository,
                 library_service: LibraryService,
                 connector_factory: MediaServerConnectorFactory):
        self.session = session
        self._repository = repository
        self._library_service = library_service
        self._connector_factory = connector_factory

    def create(self,
               media_server: MediaServer,
               libraries: List[MediaServerLibrary]) -> MediaServer:
        media_server = self._repository.create(media_server)
        for library in libraries:
            self._create_library(media_server.id, library)
        self.session.commit()
        return media_server

    def _create_library(self, media_server_id: int, library: MediaServerLibrary) -> None:
        self._library_service.create(Library(
            external_id=library.id,
            media_server_id=media_server_id,
            name=library.name,
            type=library.type,
            agent=library.agent,
            language=library.language,
            uuid=library.uuid,
            created_at=library.created_at,
            updated_at=library.updated_at,
            enabled=AppSettingsStore().get().new_library_enabled,
        ))

    def get_available_libraries(self, media_server_id: int) -> List[MediaServerLibrary]:
        self._repository.get(media_server_id)
        connector = self._connector_factory.get(media_server_id)
        try:
            remote_libraries = connector.get_libraries()
        except Exception as e:
            raise MediaServerUnreachableError(media_server_id=media_server_id) from e

        known = {library.external_id
                 for library in self._library_service.find_libraries(
                     LibrarySearch(media_server_id=media_server_id))}
        return [library for library in map(MediaServerLibrary.from_remote, remote_libraries)
                if library.id not in known]

    def add_libraries(self,
                      media_server_id: int,
                      libraries: List[MediaServerLibrary],
                      defaults: Optional[dict] = None) -> int:
        self._repository.get(media_server_id)
        if defaults:
            AppSettingsStore().partial_update(defaults)
        try:
            for library in libraries:
                self._create_library(media_server_id, library)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return len(libraries)

    def update_token(self, media_server_id: int, token: str) -> MediaServer:
        token = (token or "").strip()
        if not token:
            raise ValueError("Token is required")

        media_server = self._repository.get(media_server_id)
        media_server.token = token
        updated = self._repository.update(media_server)
        self.session.commit()

        internal_event_bus.publish_media_server_updated(media_server_id)
        return updated

    def delete(self, media_server_id: int) -> None:
        library_ids = [lib.id for lib in self._library_service.find_libraries(
            LibrarySearch(media_server_id=media_server_id))]

        if not self._repository.delete(media_server_id):
            raise MediaServerNotFoundError(media_server_id)
        self.session.commit()

        for library_id in library_ids:
            self._library_service.delete_library_poster_files(library_id)

        internal_event_bus.publish_media_server_deleted(media_server_id)

    def get(self, id: int) -> MediaServer:
        return self._repository.get(id)

    def get_by_webhook_token(self, token: str) -> Optional[MediaServer]:
        return self._repository.get_by_webhook_token(token)

    PATCHABLE_FIELDS = frozenset({
        "language_order",
        "fallback_to_server_poster",
        "skip_style_when_not_textless",
    })

    def partial_update(self, media_server_id: int, updates: dict) -> MediaServer:
        unknown = set(updates) - self.PATCHABLE_FIELDS
        if unknown:
            raise ValueError(f"Not patchable: {', '.join(sorted(unknown))}")

        media_server = self._repository.get(media_server_id)
        for field, value in updates.items():
            if field == "language_order":
                value = normalize_language_order(value)
            setattr(media_server, field, value)

        updated = self._repository.update(media_server)
        self.session.commit()
        return updated

    def set_webhook_enabled(self, media_server_id: int, enabled: bool) -> MediaServer:
        media_server = self._repository.get(media_server_id)
        media_server.webhook_enabled = enabled
        if enabled and not media_server.webhook_token:
            media_server.webhook_token = secrets.token_urlsafe(32)
        updated = self._repository.update(media_server)
        self.session.commit()
        return updated

    def regenerate_webhook_token(self, media_server_id: int) -> MediaServer:
        media_server = self._repository.get(media_server_id)
        media_server.webhook_token = secrets.token_urlsafe(32)
        updated = self._repository.update(media_server)
        self.session.commit()
        return updated

    def search(self) -> List[MediaServer]:
        return self._repository.find_all()
