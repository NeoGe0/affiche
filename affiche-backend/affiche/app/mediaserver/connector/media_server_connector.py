from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity
from affiche.app.mediaserver.model.media_server import MediaServer

class MediaServerPersistenceConnector:

    def __init__(self, session: Session):
        self._session = session

    def get(self, id: int) -> Optional[MediaServerEntity]:
        return self._session.get(MediaServerEntity, id)

    def get_by_webhook_token(self, token: str) -> Optional[MediaServerEntity]:
        stmt = select(MediaServerEntity).where(MediaServerEntity.webhook_token == token)
        return self._session.scalars(stmt).first()

    def find_all(self) -> List[MediaServerEntity]:
        stmt = select(MediaServerEntity)
        return list(self._session.scalars(stmt).all())

    def create(self, media_server: MediaServer) -> MediaServerEntity:
        entity = MediaServerEntity(
            name=media_server.name,
            type=media_server.type,
            url=media_server.url,
            token=media_server.token,
            enabled=media_server.enabled,
            language_order=media_server.language_order,
        )
        self._session.add(entity)
        self._session.flush()
        return entity

    def update(self, media_server: MediaServer) -> Optional[MediaServerEntity]:
        entity = self._session.get(MediaServerEntity, media_server.id)
        if entity is None:
            return None
        entity.url = media_server.url
        entity.token = media_server.token
        entity.enabled = media_server.enabled
        entity.language_order = media_server.language_order
        entity.fallback_to_server_poster = media_server.fallback_to_server_poster
        entity.skip_style_when_not_textless = media_server.skip_style_when_not_textless
        entity.webhook_enabled = media_server.webhook_enabled
        entity.webhook_token = media_server.webhook_token
        self._session.flush()
        return entity

    def delete(self, id: int) -> bool:
        entity = self._session.get(MediaServerEntity, id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.flush()
        return True
