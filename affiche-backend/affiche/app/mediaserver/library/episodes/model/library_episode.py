from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class LibraryEpisode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    season_id: int
    show_id: int
    library_id: int
    external_id: str
    season_number: int
    episode_number: int
    title: str
    air_date: Optional[datetime] = None
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None

    media_resolution: Optional[str] = None
    media_width: Optional[int] = None
    media_height: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    media_container: Optional[str] = None
    media_bitrate: Optional[int] = None
    media_size_bytes: Optional[int] = None
