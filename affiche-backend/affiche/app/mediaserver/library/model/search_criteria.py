from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class SortDir(str, Enum):
    ASC = "asc"
    DESC = "desc"

class SearchCriteria(BaseModel):
    model_config = ConfigDict(frozen=True)

    sort_by: str = 'title'
    sort_dir: SortDir = SortDir.ASC

    page: int = Field(0, ge=0)
    page_size: Optional[int] = Field(None, ge=1)

    @property
    def offset(self) -> int:
        return 0 if self.page_size is None else self.page * self.page_size

    @property
    def limit(self) -> Optional[int]:
        return self.page_size
