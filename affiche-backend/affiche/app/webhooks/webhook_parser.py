from dataclasses import dataclass
from typing import Optional

@dataclass
class WebhookEvent:
    is_new_item: bool
    library_external_id: Optional[str] = None

def parse_plex(payload: dict) -> WebhookEvent:
    is_new = payload.get("event") == "library.new"
    section = (payload.get("Metadata") or {}).get("librarySectionID")
    return WebhookEvent(
        is_new_item=is_new,
        library_external_id=str(section) if section is not None else None,
    )

def parse_jellyfin(payload: dict) -> WebhookEvent:
    is_new = payload.get("NotificationType") == "ItemAdded"
    section = (
        payload.get("LibraryId")
        or payload.get("CollectionFolderId")
        or payload.get("ParentId")
    )
    return WebhookEvent(
        is_new_item=is_new,
        library_external_id=str(section) if section else None,
    )
