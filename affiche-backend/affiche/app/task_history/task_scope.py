from typing import Optional, Tuple

def parse_task_scope(resource: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    if not resource:
        return None, None

    parts = resource.split(":")
    if len(parts) < 2 or parts[0] != "ms":
        return None, None

    media_server_id = _as_int(parts[1])
    if media_server_id is None:
        return None, None
    if len(parts) >= 4 and parts[2] == "lib":
        return media_server_id, _as_int(parts[3])
    return media_server_id, None

def _as_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None
