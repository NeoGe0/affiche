from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class LibraryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    library_id: int
    external_id: str
    title: str
    type: str
    year: Optional[int] = None
    release_date: Optional[datetime] = None
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    poster_uploaded_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None

    poster_url: Optional[str] = None
    poster_hash: Optional[str] = None
    poster_provider: Optional[str] = None
    style_hash: Optional[str] = None
    processed: bool = False
    locked: bool = False
    error_message: Optional[str] = None

    media_resolution: Optional[str] = None
    media_width: Optional[int] = None
    media_height: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    media_container: Optional[str] = None
    media_bitrate: Optional[int] = None
    media_size_bytes: Optional[int] = None
