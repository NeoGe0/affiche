from typing import List, Optional

from pydantic import BaseModel

class ItemStats(BaseModel):
    total: int
    processed: int
    unprocessed: int
    errors: int
    locked: int
    uploaded: int

    class Config:
        from_attributes = True

class DashboardLibraryResponse(BaseModel):
    library_id: int
    library_name: str
    library_type: str
    enabled: bool
    media_server_id: int
    media_server_name: str
    media_server_type: str
    stats: ItemStats

    class Config:
        from_attributes = True

class ProviderShareResponse(BaseModel):
    provider: str
    count: int

    class Config:
        from_attributes = True

class DashboardTask(BaseModel):
    task_id: str
    task_name: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

class ProviderDayResponse(BaseModel):
    day: str
    provider: str
    count: int

class ProviderHistoryResponse(BaseModel):
    days: int
    series: List[ProviderDayResponse]
    totals: List[ProviderShareResponse]

class DashboardResponse(BaseModel):
    totals: ItemStats
    library_count: int
    media_server_count: int
    libraries: List[DashboardLibraryResponse]
    providers: List[ProviderShareResponse]
    recent_tasks: List[DashboardTask]
