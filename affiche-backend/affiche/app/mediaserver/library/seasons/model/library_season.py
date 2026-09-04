from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

class LibrarySeason(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    show_id: int
    library_id: int
    external_id: str
    season_number: int
    title: str
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None

    poster_url: Optional[str] = None
    poster_hash: Optional[str] = None
    poster_provider: Optional[str] = None
    style_hash: Optional[str] = None
    processed: bool = False

class SeasonPosterState(BaseModel):
    model_config = ConfigDict(frozen=True)

    processed: Optional[bool] = None
    poster_hash: Optional[str] = None
    poster_provider: Optional[str] = None
    style_hash: Optional[str] = None

    def changes(self) -> Dict[str, Any]:
        return self.model_dump(exclude_unset=True)
