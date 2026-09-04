import logging
import threading
from typing import Dict, Callable

from sqlalchemy.orm import Session

from affiche.app.mediaserver.service.media_server_connector_protocol import MediaServerConnector
from affiche.app.mediaserver.model.media_server import MediaServer
from affiche.app.mediaserver.service.media_server_repository import MediaServerRepository
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService
from affiche.external.plex.service.plex_service import PlexService

logger = logging.getLogger(__name__)

class MediaServerConnectorFactory:

    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory
        self._cache: Dict[int, MediaServerConnector] = {}
        self._lock = threading.Lock()

    def get(self, media_server_id: int) -> MediaServerConnector:
        if media_server_id not in self._cache:
            with self._lock:
                if media_server_id not in self._cache:
                    self._cache[media_server_id] = self._create_connector(media_server_id)
                    logger.debug("Created new connector for media server %d", media_server_id)

        return self._cache[media_server_id]

    def invalidate(self, media_server_id: int) -> None:
        with self._lock:
            if media_server_id in self._cache:
                del self._cache[media_server_id]
                logger.info("Invalidated connector cache for media server %d", media_server_id)

    def _create_connector(self, media_server_id: int) -> MediaServerConnector:
        session = self._session_factory()
        try:
            media_server = MediaServerRepository(session).get(media_server_id)
            return self._create_connector_for_type(media_server)
        finally:
            session.close()

    def _create_connector_for_type(self, media_server: MediaServer) -> MediaServerConnector:
        match media_server.type:
            case 'PLEX':
                return PlexService(media_server.url, media_server.token)
            case 'JELLYFIN':
                return JellyfinService(media_server.url, media_server.token)
            case _:
                raise ValueError(f"Unknown media server type: {media_server.type}")
