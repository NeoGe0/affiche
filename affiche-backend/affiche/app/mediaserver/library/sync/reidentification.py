from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

GUID_FIELDS = ("imdb_id", "tmdb_id", "tvdb_id")

@dataclass(frozen=True)
class SplitItem:
    stale_id: int
    fresh_id: int
    external_id: str

@dataclass(frozen=True)
class RemoteIdentity:
    external_id: str
    type: str
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None

def _guid_keys(record) -> List[Tuple[str, str, str]]:
    keys = []
    for field in GUID_FIELDS:
        value = getattr(record, field, None)
        if value is None:
            continue
        text = str(value).strip().lower()
        if text:
            keys.append((field, text, record.type))
    return keys

def _index(records: Iterable) -> Dict[Tuple[str, str, str], list]:
    index: Dict[Tuple[str, str, str], list] = {}
    for record in records:
        for key in _guid_keys(record):
            index.setdefault(key, []).append(record)
    return index

def match_readded_items(existing: Sequence,
                        incoming: Sequence[RemoteIdentity]) -> Dict[int, str]:
    incoming_ids = {identity.external_id for identity in incoming}
    existing_ids = {row.external_id for row in existing}

    departing = _index(row for row in existing if row.external_id not in incoming_ids)
    arriving = [identity for identity in incoming if identity.external_id not in existing_ids]
    arriving_index = _index(arriving)

    adoptions: Dict[int, str] = {}
    claimed_rows: set = set()

    for identity in arriving:
        for key in _guid_keys(identity):
            candidates = departing.get(key, [])
            if len(candidates) != 1 or len(arriving_index.get(key, [])) != 1:
                continue
            row = candidates[0]
            if row.id in claimed_rows:
                continue
            adoptions[row.id] = identity.external_id
            claimed_rows.add(row.id)
            break

    return adoptions

def match_readded_seasons(existing: Sequence,
                          incoming: Mapping[int, str]) -> Dict[int, str]:
    known = set(incoming.values())
    return {
        season.id: incoming[season.season_number]
        for season in existing
        if season.season_number in incoming
        and season.external_id != incoming[season.season_number]
        and season.external_id not in known
    }

def match_split_items(existing: Sequence,
                      incoming: Sequence[RemoteIdentity]) -> List[SplitItem]:
    incoming_ids = {identity.external_id for identity in incoming}
    departed = _index(row for row in existing if row.external_id not in incoming_ids)
    present = _index(row for row in existing if row.external_id in incoming_ids)

    splits: List[SplitItem] = []
    claimed: set = set()

    for key, stale_rows in departed.items():
        fresh_rows = present.get(key, [])
        if len(stale_rows) != 1 or len(fresh_rows) != 1:
            continue
        stale, fresh = stale_rows[0], fresh_rows[0]
        if stale.id in claimed or fresh.id in claimed:
            continue
        splits.append(SplitItem(stale_id=stale.id, fresh_id=fresh.id,
                                external_id=fresh.external_id))
        claimed.update({stale.id, fresh.id})

    return splits
