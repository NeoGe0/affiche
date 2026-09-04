from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

from affiche.config.language_config import DEFAULT_LANGUAGE_ORDER

class MediaServerType(str, Enum):
    PLEX = "PLEX"
    JELLYFIN = "JELLYFIN"

class MediaServerLibrary(BaseModel):
    id: str
    name: str
    type: str
    item_count: int
    agent: Optional[str] = None
    language: str
    uuid: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_remote(cls, library) -> "MediaServerLibrary":
        return cls(
            id=str(library.id),
            name=library.name,
            type=library.type,
            item_count=library.item_count,
            agent=getattr(library, "agent", None),
            language=library.language,
            uuid=getattr(library, "uuid", None),
            created_at=library.created_at,
            updated_at=library.updated_at,
        )

class MediaServer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str
    type: MediaServerType
    token: str
    url: str
    enabled: bool = True
    language_order: list[str] = DEFAULT_LANGUAGE_ORDER
    fallback_to_server_poster: bool = False
    skip_style_when_not_textless: bool = False
    webhook_enabled: bool = False
    webhook_token: Optional[str] = None
    last_sync: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
