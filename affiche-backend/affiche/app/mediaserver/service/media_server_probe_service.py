import logging
from typing import Callable, List, NamedTuple, TypeVar

import requests
from plexapi.exceptions import Unauthorized

from affiche.app.mediaserver.model.media_server import (
    MediaServer,
    MediaServerLibrary,
    MediaServerType,
)
from affiche.app.service_configuration.exceptions import (
    MediaServerCredentialsRejectedError,
    MediaServerUnreachableError,
)
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService
from affiche.external.plex.service.plex_service import PlexService

logger = logging.getLogger(__name__)

T = TypeVar("T")

_CREDENTIAL_NAMES = {
    MediaServerType.PLEX: "token",
    MediaServerType.JELLYFIN: "API key",
}

class MediaServerProbe(NamedTuple):
    name: str
    libraries: List[MediaServerLibrary]

class MediaServerProbeService:

    def probe(self, server_type: MediaServerType, url: str, token: str) -> MediaServerProbe:
        connector = _connector(server_type, url, token)
        info, libraries = self._attempt(
            server_type, lambda: (connector.get_server_info(), connector.get_libraries()))
        return MediaServerProbe(
            name=info["friendly_name"],
            libraries=[MediaServerLibrary.from_remote(library) for library in libraries],
        )

    def verify_token(self, media_server: MediaServer, token: str) -> None:
        connector = _connector(media_server.type, media_server.url, token)
        self._attempt(media_server.type, connector.get_server_info)

    def _attempt(self, server_type: MediaServerType, action: Callable[[], T]) -> T:
        label = server_type.value.capitalize()
        try:
            return action()
        except Unauthorized:
            raise MediaServerCredentialsRejectedError(label, _CREDENTIAL_NAMES[server_type])
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (401, 403):
                raise MediaServerCredentialsRejectedError(label, _CREDENTIAL_NAMES[server_type])
            logger.exception("Could not reach %s at the configured URL", label)
            raise MediaServerUnreachableError(label) from e
        except Exception as e:
            logger.exception("Could not reach %s at the configured URL", label)
            raise MediaServerUnreachableError(label) from e

def _connector(server_type: MediaServerType, url: str, token: str):
    if MediaServerType(server_type) == MediaServerType.PLEX:
        return PlexService(url, token)
    return JellyfinService(url, token)
