from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from affiche.app.mediaserver.library.model import SearchCriteria, SortDir

class TaskRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    task_id: str
    task_name: str
    status: str

    resource: Optional[str] = None
    media_server_id: Optional[int] = None
    library_id: Optional[int] = None
    blocking: bool = False

    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    items_done: Optional[int] = None
    items_total: Optional[int] = None

    message: Optional[str] = None
    error: Optional[str] = None

class TaskRunSearch(SearchCriteria):
    library_id: Optional[int] = None

    sort_by: str = 'created_at'
    sort_dir: SortDir = SortDir.DESC
