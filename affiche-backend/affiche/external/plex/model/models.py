from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class PlexLibrary(BaseModel):
    class Config:
        from_attributes = True

    id: str
    name: str
    type: str
    item_count: int
    agent: str
    language: str
    uuid: str
    created_at: datetime
    updated_at: datetime

class PlexLibraryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    library_id: str
    title: str
    type: str
    year: Optional[int] = None
    release_date: Optional[datetime] = None
    added_at: datetime
    updated_at: datetime

    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    poster_url: Optional[str] = None

    media_resolution: Optional[str] = None
    media_width: Optional[int] = None
    media_height: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    media_container: Optional[str] = None
    media_bitrate: Optional[int] = None
    media_size_bytes: Optional[int] = None

class PlexSeason(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    show_id: str
    library_id: str
    season_number: int
    title: str
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    poster_url: Optional[str] = None

class PlexCollection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    library_id: str
    title: str
    sort_title: Optional[str] = None
    child_count: Optional[int] = None
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    poster_url: Optional[str] = None
    member_external_ids: list[str] = []

class PlexEpisode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    season_external_id: str
    library_id: str
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
