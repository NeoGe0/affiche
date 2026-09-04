from typing import List

TEXTLESS = ""

SUPPORTED_LANGUAGES = ["en", "fr", "de", "es", "it", "pt", "nl", "ja", "ko", "zh"]

DEFAULT_LANGUAGE_ORDER = [TEXTLESS, "en", "fr"]

def normalize_language_order(order: List[str] | None) -> List[str]:
    allowed = {TEXTLESS, *SUPPORTED_LANGUAGES}
    seen: set[str] = set()
    result: List[str] = []
    for language in order or []:
        code = (language or TEXTLESS).strip().lower()
        if code in allowed and code not in seen:
            seen.add(code)
            result.append(code)
    return result or [TEXTLESS]
