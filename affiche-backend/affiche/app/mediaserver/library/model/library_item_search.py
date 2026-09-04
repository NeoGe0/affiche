from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import model_validator

from affiche.app.mediaserver.library.model.search_criteria import SearchCriteria

class ItemStatusFilter(str, Enum):
    UNPROCESSED = "unprocessed"
    ERRORS = "errors"
    LOCKED = "locked"

NO_PROVIDER = "none"

class LibraryItemSearch(SearchCriteria):

    library_id: Optional[int] = None
    library_ids: Optional[List[int]] = None

    search: Optional[str] = None
    processed: Optional[bool] = None
    has_error: Optional[bool] = None
    status: Optional[ItemStatusFilter] = None
    locked: Optional[bool] = None
    provider: Optional[str] = None
    attempted: Optional[bool] = None
    uploaded: Optional[bool] = None
    external_ids: Optional[List[str]] = None
    item_ids: Optional[List[int]] = None
    deleted: Optional[bool] = False
    deleted_before: Optional[datetime] = None

    @model_validator(mode='after')
    def _expand_and_check(self) -> 'LibraryItemSearch':
        if self.status is not None:
            if self.processed is not None or self.has_error is not None or self.locked is not None:
                raise ValueError("pass either `status` or `processed`/`has_error`/`locked`, not both")
            expanded = {
                ItemStatusFilter.UNPROCESSED: {'processed': False, 'has_error': False},
                ItemStatusFilter.ERRORS: {'has_error': True},
                ItemStatusFilter.LOCKED: {'locked': True},
            }[self.status]
            for field, value in expanded.items():
                object.__setattr__(self, field, value)

        if self.deleted_before is not None and self.deleted is not True:
            raise ValueError("`deleted_before` only means something with `deleted=True`")

        if self.library_id is None and not self.library_ids and self.deleted is not True:
            raise ValueError("a search must be scoped to a library unless it is a trash sweep")

        return self
