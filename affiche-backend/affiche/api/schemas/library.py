from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List, Tuple

from fastapi import HTTPException
from pydantic import BaseModel, Field

from affiche.api.schemas.settings_schema import OverlayOptionsResponse, TextOptionsResponse
from affiche.app.filestore.filestore import FileStoreService
from affiche.app.image import custom_poster
from affiche.app.image.model import OverlayOptions, TextOptions
from affiche.app.mediaserver.library.model import ItemStatusFilter, LibraryItemSearch, SortDir

PROCESSED_NO_POSTER_ERROR = "Marked as processed but no poster was generated — this item needs attention."

class ErrorCause(str, Enum):

    IDENTIFIER_MISMATCH = "identifier_mismatch"

def _error_cause(item, error: Optional[str]) -> Optional[ErrorCause]:
    if not error:
        return None
    if getattr(item, "imdb_id", None) or getattr(item, "tvdb_id", None):
        return None
    return ErrorCause.IDENTIFIER_MISMATCH

def _effective_error(item, has_poster: bool) -> Optional[str]:
    if item.error_message:
        return item.error_message
    if item.processed and not has_poster:
        return PROCESSED_NO_POSTER_ERROR
    return None

class LibraryBase(BaseModel):
    name: str
    library_type: str

class Library(LibraryBase):
    id: int
    media_server_id: int
    agent: Optional[str] = None
    scanner: Optional[str] = None
    language: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    media_count: Optional[int] = None
    enabled: Optional[bool] = True

    class Config:
        from_attributes = True

class LibraryItemResponse(BaseModel):
    id: int
    library_id: int
    external_id: Optional[str] = None
    title: str
    type: str
    year: Optional[int] = None
    release_date: Optional[datetime] = None
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    poster_uploaded_at: Optional[datetime] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None
    processed: bool = False
    locked: bool = False
    poster_provider: Optional[str] = None
    error_message: Optional[str] = None
    error_cause: Optional[ErrorCause] = None
    has_poster: bool = False
    poster_version: Optional[str] = None
    source_poster_version: Optional[str] = None
    media_resolution: Optional[str] = None
    media_width: Optional[int] = None
    media_height: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    audio_channels: Optional[int] = None
    media_container: Optional[str] = None
    media_bitrate: Optional[int] = None
    media_size_bytes: Optional[int] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def of(cls, library_id: int, item, store: FileStoreService) -> "LibraryItemResponse":
        resp = cls.model_validate(item)
        resp.poster_version = store.version(library_id, item.id)
        resp.has_poster = resp.poster_version is not None
        resp.source_poster_version = store.source_version(library_id, item.id)
        resp.error_message = _effective_error(item, resp.has_poster)
        resp.error_cause = _error_cause(item, item.error_message)
        return resp

class ItemSeason(BaseModel):
    id: int
    show_id: int
    library_id: int
    season_number: int
    title: str
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None

    poster_url: Optional[str] = None
    poster_provider: Optional[str] = None
    processed: bool
    has_poster: bool = False
    poster_version: Optional[str] = None
    source_poster_version: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def of(cls, library_id: int, item_id: int, season, store: FileStoreService) -> "ItemSeason":
        resp = cls.model_validate(season)
        resp.poster_version = store.version(library_id, item_id,
                                            season_number=season.season_number)
        resp.has_poster = resp.poster_version is not None
        resp.source_poster_version = store.source_version(library_id, item_id,
                                                          season_number=season.season_number)
        return resp

class LibraryItemWithSeasons(LibraryItemResponse):
    seasons: List[ItemSeason] = []

class ItemEpisode(BaseModel):
    id: int
    season_id: int
    show_id: int
    library_id: int
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

    class Config:
        from_attributes = True

class LibraryWithItems(Library):
    items: List[LibraryItemResponse] = []

class PaginatedLibraryItems(BaseModel):
    items: List[LibraryItemResponse]
    total: int
    total_pages: int
    page: int
    page_size: int

    @classmethod
    def of(cls, items: List[LibraryItemResponse], total: int,
           search: LibraryItemSearch, page_size: int) -> 'PaginatedLibraryItems':
        return cls(
            items=items,
            total=total,
            total_pages=-(-total // page_size),
            page=search.page,
            page_size=page_size,
        )

class LibraryItemQuery(BaseModel):
    search: Optional[str] = None
    status: Optional[ItemStatusFilter] = None
    provider: Optional[str] = None
    sort_by: str = 'title'
    sort_dir: SortDir = SortDir.ASC
    page: int = Field(0, ge=0)
    page_size: int = Field(50, ge=1)

    def to_domain(self, library_id: int, **overrides) -> LibraryItemSearch:
        return LibraryItemSearch(**{**self.model_dump(), 'library_id': library_id, **overrides})

class LibraryItemCounts(BaseModel):
    total: int
    unprocessed: int
    errors: int
    locked: int
    providers: Dict[str, int] = {}

class LibraryStyleStaleness(BaseModel):
    stale: int
    total: int

class ItemLockRequest(BaseModel):
    locked: bool

class ItemSelectionRequest(BaseModel):
    item_ids: List[int] = Field(..., min_length=1)

class ItemSelectionLockRequest(ItemSelectionRequest):
    locked: bool

class BulkLockResponse(BaseModel):
    changed: int

class AlphaIndexEntry(BaseModel):
    letter: str
    page: int

class TrashEmptyResponse(BaseModel):
    purged: int

class SyncTaskResponse(BaseModel):
    status: str
    task_id: str
    message: Optional[str] = None

class ApplyPosterRequest(BaseModel):
    poster_url: str
    jpeg_quality: Optional[int] = None
    title: Optional[str] = None
    upload: Optional[bool] = None
    overlay_options: Optional[OverlayOptionsResponse] = None
    text_options: Optional[TextOptionsResponse] = None

    def style_overrides(self) -> Tuple[Optional[OverlayOptions], Optional[TextOptions]]:
        try:
            overlay = OverlayOptions(**self.overlay_options.model_dump()) if self.overlay_options else None
            text = TextOptions(**self.text_options.model_dump()) if self.text_options else None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return overlay, text

    def resolved_poster_source(self) -> str:
        try:
            return custom_poster.resolve_source(self.poster_url)
        except custom_poster.CustomPosterError as e:
            raise HTTPException(status_code=400, detail=str(e))
