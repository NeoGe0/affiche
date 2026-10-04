import re
import unicodedata

_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)

_CONJUNCTIONS = frozenset({"and", "et", "und", "en"})

def normalise(title: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (title or "").strip())
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    words = _PUNCTUATION.sub(" ", stripped).casefold().split()
    return " ".join(word for word in words if word not in _CONJUNCTIONS)

def matches_any(server_title: str, candidates) -> bool:
    return any(not titles_differ(server_title, candidate) for candidate in candidates or ())

def titles_differ(server_title: str, catalogue_title: str) -> bool:
    if not (server_title or "").strip() or not (catalogue_title or "").strip():
        return False
    return normalise(server_title) != normalise(catalogue_title)
