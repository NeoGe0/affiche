from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

class StyleProfileResponse(BaseModel):
    id: int
    name: str
    overlay_options: dict[str, Any] | None = None
    text_options: dict[str, Any] | None = None
    library_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class StyleProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    overlay_options: dict[str, Any] | None = None
    text_options: dict[str, Any] | None = None

class StyleProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    overlay_options: dict[str, Any] | None = None
    text_options: dict[str, Any] | None = None
