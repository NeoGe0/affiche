from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field

from affiche.app.mediaserver.library.settings.model.library_settings import AutoPickupAction

class LibrarySettingsResponse(BaseModel):
    library_id: int
    enabled: bool
    upload_enabled: bool
    provider_order: List[str]
    overlay_options: dict[str, Any] | None = None
    text_options: dict[str, Any] | None = None
    style_profile_id: int | None = None
    track_episodes: bool = False
    track_collections: bool = False
    auto_sync_enabled: bool = False
    auto_sync_interval_minutes: int = 360
    auto_pickup_action: AutoPickupAction = AutoPickupAction.SYNC
    last_auto_sync_at: datetime | None = None
    last_full_sync_at: datetime | None = None

class LibrarySettingsUpdate(BaseModel):
    enabled: bool | None = None
    upload_enabled: bool | None = None
    provider_order: List[str] | None = None
    overlay_options: dict[str, Any] | None = None
    text_options: dict[str, Any] | None = None
    style_profile_id: int | None = None
    track_episodes: bool | None = None
    track_collections: bool | None = None
    auto_sync_enabled: bool | None = None
    auto_sync_interval_minutes: int | None = Field(default=None, ge=5)
    auto_pickup_action: AutoPickupAction | None = None
