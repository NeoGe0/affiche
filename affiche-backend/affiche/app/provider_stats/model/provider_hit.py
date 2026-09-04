from datetime import date, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

RETENTION_DAYS = 365

DEFAULT_WINDOW_DAYS = 30

class ProviderHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    provider: str
    library_id: int
    count: int

class ProviderDay(BaseModel):
    day: date
    provider: str
    count: int

class ProviderStatsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    days: int = Field(DEFAULT_WINDOW_DAYS, ge=1, le=RETENTION_DAYS)
    library_id: Optional[int] = None

    @property
    def since(self) -> date:
        return date.today() - timedelta(days=self.days - 1)
