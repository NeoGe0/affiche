from datetime import datetime
from typing import List, NamedTuple, Optional, Protocol

class ResetResult(NamedTuple):
    success: bool
    poster_url: Optional[str] = None

class MediaServerConnector(Protocol):

    def upload_poster(self, external_id: str, poster_path: str) -> bool:
        ...

    def reset_poster(self, external_id: str) -> ResetResult:
        ...

    def get_poster_url(self, external_id: str) -> Optional[str]:
        ...

class RemoteLibrary(Protocol):
    id: str
    name: str
    type: str
    item_count: int
    language: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class LibraryEnumerator(Protocol):

    def get_libraries(self) -> List[RemoteLibrary]:
        ...

class CollectionWriter(Protocol):

    def create_collection(self, library_external_id: str, title: str,
                          item_external_ids: List[str]) -> Optional[str]:
        ...

    def rename_collection(self, external_id: str, title: str) -> bool:
        ...

    def delete_collection(self, external_id: str) -> bool:
        ...

    def add_to_collection(self, external_id: str, item_external_ids: List[str]) -> bool:
        ...

    def remove_from_collection(self, external_id: str, item_external_ids: List[str]) -> bool:
        ...
