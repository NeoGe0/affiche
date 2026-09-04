from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

from affiche.config.library_config import DEFAULT_PROVIDER_ORDER

class AutoPickupAction(str, Enum):
    SYNC = "sync"
    GENERATE = "generate"
    UPLOAD = "upload"

class LibrarySettings(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    library_id: int
    upload_enabled: bool = True
    provider_order: list[str] = DEFAULT_PROVIDER_ORDER
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
