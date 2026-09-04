import logging
import re

_SECRET_PARAM_RE = re.compile(
    r"(?i)((?:X-Plex-Token|X-Emby-Token|api[-_]?key|client_key|token)=)[^&\s\"'>]+"
)

def redact_secrets(text) -> str:
    if not isinstance(text, str):
        text = str(text)
    return _SECRET_PARAM_RE.sub(r"\1***", text)

class RedactingFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        return redact_secrets(super().format(record))
