from typing import Callable, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.model.media_server import MediaServerType
from affiche.app.mediaserver.service.jellyfin_sync_service import JellyfinSynchronisationService
from affiche.app.mediaserver.service.media_server_service import MediaServerService
from affiche.app.mediaserver.service.plex_sync_service import PlexSynchronisationService
from affiche.config.exceptions.exceptions import ItemMissingOnMediaServerException

CancelCheck = Optional[Callable[[], bool]]

class MediaServerSynchronisationService:

    def __init__(self,
                 session: Session,
                 media_server_service: MediaServerService,
                 plex_sync_service: PlexSynchronisationService,
                 jellyfin_sync_service: JellyfinSynchronisationService):
        self.session = session
        self.media_server_service = media_server_service
        self.plex_sync_service = plex_sync_service
        self.jellyfin_sync_service = jellyfin_sync_service

    def sync_library(self,
                     media_server_id: int,
                     library_id: int,
                     cancel_check: CancelCheck = None,
                     incremental: bool = False):
        media_server = self.media_server_service.get(media_server_id)
        if media_server.type == MediaServerType.PLEX:
            self.plex_sync_service.sync_plex_library(media_server, library_id,
                                                     cancel_check=cancel_check,
                                                     incremental=incremental)
        elif media_server.type == MediaServerType.JELLYFIN:
            self.jellyfin_sync_service.sync_jellyfin_library(media_server, library_id,
                                                             cancel_check=cancel_check,
                                                             incremental=incremental)
        else:
            raise ValueError(f"Unsupported media server type: {media_server.type}")

    def sync_item(self,
                  media_server_id: int,
                  library_id: int,
                  item_id: int):
        media_server = self.media_server_service.get(media_server_id)
        if media_server.type == MediaServerType.PLEX:
            item = self.plex_sync_service.sync_plex_item(media_server, library_id, item_id)
        elif media_server.type == MediaServerType.JELLYFIN:
            item = self.jellyfin_sync_service.sync_jellyfin_item(media_server, library_id, item_id)
        else:
            raise ValueError(f"Unsupported media server type: {media_server.type}")

        if item is None:
            raise ItemMissingOnMediaServerException(item_id)
        self.session.commit()
        return item

    def sync_libraries(self,
                       media_server_id: int,
                       cancel_check: CancelCheck = None):
        media_server = self.media_server_service.get(media_server_id)
        if media_server.type == MediaServerType.PLEX:
            self.plex_sync_service.sync_plex_libraries(media_server, cancel_check=cancel_check)
        elif media_server.type == MediaServerType.JELLYFIN:
            self.jellyfin_sync_service.sync_jellyfin_libraries(media_server, cancel_check=cancel_check)
        else:
            raise ValueError(f"Unsupported media server type: {media_server.type}")
