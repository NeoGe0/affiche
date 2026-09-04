from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.mediaserver.connector.media_server_connector import MediaServerPersistenceConnector
from affiche.app.mediaserver.model.media_server import MediaServer
from affiche.app.service_configuration.exceptions import MediaServerNotFoundError

class MediaServerRepository:

    def __init__(self, session: Session):
        self._connector = MediaServerPersistenceConnector(session)

    def get(self, id: int) -> MediaServer:
        configuration = self._connector.get(id)
        if configuration is None:
            raise MediaServerNotFoundError(id)
        return MediaServer.model_validate(configuration)

    def get_by_webhook_token(self, token: str) -> Optional[MediaServer]:
        entity = self._connector.get_by_webhook_token(token)
        return MediaServer.model_validate(entity) if entity else None

    def find_all(self) -> List[MediaServer]:
        configurations = self._connector.find_all()
        return [MediaServer.model_validate(configuration) for configuration in configurations]

    def create(self, media_server: MediaServer) -> MediaServer:
        configuration = self._connector.create(media_server)
        return MediaServer.model_validate(configuration)

    def update(self, media_server: MediaServer) -> MediaServer:
        configuration = self._connector.update(media_server)
        if configuration is None:
            raise MediaServerNotFoundError(media_server.id)
        return MediaServer.model_validate(configuration)

    def delete(self, id: int) -> bool:
        return self._connector.delete(id)
