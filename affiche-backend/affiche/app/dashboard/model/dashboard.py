from typing import List

from pydantic import BaseModel

from affiche.app.mediaserver.library.model.library_item_stats import LibraryItemStats

class DashboardLibrary(BaseModel):
    library_id: int
    library_name: str
    library_type: str
    enabled: bool
    media_server_id: int
    media_server_name: str
    media_server_type: str
    stats: LibraryItemStats

class ProviderShare(BaseModel):
    provider: str
    count: int

class DashboardSummary(BaseModel):
    totals: LibraryItemStats
    library_count: int
    media_server_count: int
    libraries: List[DashboardLibrary]
    providers: List[ProviderShare]
