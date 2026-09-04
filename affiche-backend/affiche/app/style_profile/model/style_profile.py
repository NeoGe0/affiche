from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

class StyleProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    overlay_options: dict[str, Any] | None = None
    text_options: dict[str, Any] | None = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
