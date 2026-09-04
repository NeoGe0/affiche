from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from affiche.app.mediaserver.model.media_server import MediaServerLibrary, MediaServerType

__all__ = [
    "AddLibrariesRequest",
    "JellyfinServiceCredentials",
    "LanguageOrderUpdate",
    "MediaServerCreate",
    "MediaServerLibrary",
    "MediaServerResponse",
    "MediaServerTestResult",
    "MediaServerTokenUpdate",
    "PlexServiceCredentials",
    "PosterFallbackUpdate",
    "WebhookUpdate",
]

class PlexServiceCredentials(BaseModel):
    url: str
    token: str

class JellyfinServiceCredentials(BaseModel):
    url: str
    api_key: str

class MediaServerTestResult(BaseModel):
    name: str
    libraries: List[MediaServerLibrary]

class MediaServerCreate(BaseModel):
    name: str
    type: MediaServerType
    url: str
    token: str
    enabled: bool = True
    libraries: List[MediaServerLibrary]

class AddLibrariesRequest(BaseModel):
    libraries: List[MediaServerLibrary]
    new_library_enabled: Optional[bool] = None
    new_library_upload_enabled: Optional[bool] = None
    new_library_provider_order: Optional[List[str]] = None

class MediaServerResponse(BaseModel):
    id: int
    name: str
    type: MediaServerType
    url: str
    enabled: bool
    language_order: List[str]
    fallback_to_server_poster: bool = False
    skip_style_when_not_textless: bool = False
    webhook_enabled: bool = False
    webhook_token: str | None = None
    last_sync: datetime | None
    created_at: datetime
    updated_at: datetime

class MediaServerTokenUpdate(BaseModel):
    token: str

class WebhookUpdate(BaseModel):
    enabled: bool

class LanguageOrderUpdate(BaseModel):
    language_order: List[str]

class PosterFallbackUpdate(BaseModel):
    fallback_to_server_poster: Optional[bool] = None
    skip_style_when_not_textless: Optional[bool] = None
