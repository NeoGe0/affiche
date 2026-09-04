from typing import List, Tuple

from affiche.app.mediaserver.library.model import Library, LibraryItem, LibraryItemSearch, LibrarySearch
from affiche.app.mediaserver.library.service.library_repository import LibraryRepository

def resolve_selection(repo: LibraryRepository,
                      media_server_id: int,
                      item_ids: List[int]) -> List[Tuple[Library, List[LibraryItem]]]:
    if not item_ids:
        return []

    libraries = {library.id: library for library in repo.find_libraries(LibrarySearch(media_server_id=media_server_id))}
    if not libraries:
        return []

    items = repo.find_items(LibraryItemSearch(library_ids=list(libraries), item_ids=item_ids))

    grouped: dict[int, List[LibraryItem]] = {}
    for item in items:
        grouped.setdefault(item.library_id, []).append(item)

    return [(libraries[library_id], selected) for library_id, selected in grouped.items()]
