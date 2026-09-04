import logging

import pytest

from affiche.app.service_configuration.exceptions import ProviderConnectionError
from affiche.app.service_configuration.provider_service import ProviderService
from affiche.config.redaction import RedactingFormatter, redact_secrets

@pytest.mark.parametrize("raw, secret", [
    ("https://plex.local/library?X-Plex-Token=abc123DEF", "abc123DEF"),
    ("https://webservice.fanart.tv/v3/movies/550?api_key=SECRETKEY", "SECRETKEY"),
    ("http://jf.local/Items?X-Emby-Token=embytoken99", "embytoken99"),
    ("GET /x?client_key=ck_live_xyz", "ck_live_xyz"),
    ("some blob token=raw_token_val end", "raw_token_val"),
    ("call?api-key=hyphenated123", "hyphenated123"),
])
def test_redacts_known_secrets(raw, secret):
    result = redact_secrets(raw)
    assert secret not in result
    assert "***" in result

def test_redaction_is_case_insensitive():
    assert "abc" not in redact_secrets("?x-plex-TOKEN=abc")

def test_non_secret_text_unchanged():
    text = "Connection refused to host plex.local:32400 (max retries exceeded)"
    assert redact_secrets(text) == text

def test_non_string_input_is_coerced():
    assert redact_secrets(12345) == "12345"

def test_preserves_trailing_query_params():
    out = redact_secrets("https://x/y?api_key=SECRET&page=2")
    assert "SECRET" not in out
    assert "page=2" in out

def test_formatter_scrubs_message():
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="t", level=logging.ERROR, pathname=__file__, lineno=1,
        msg="GET /library?X-Plex-Token=leakme", args=(), exc_info=None,
    )
    out = formatter.format(record)
    assert "leakme" not in out
    assert "X-Plex-Token=***" in out

def test_formatter_scrubs_traceback():
    formatter = RedactingFormatter("%(message)s")
    try:
        raise ValueError("upstream failed for url https://plex/?X-Plex-Token=tracebacksecret")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="t", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="boom", args=(), exc_info=sys.exc_info(),
        )
    out = formatter.format(record)
    assert "tracebacksecret" not in out
    assert "***" in out

def test_provider_connection_error_does_not_carry_secret(monkeypatch):
    service = ProviderService()

    def boom(self, api_token):
        raise Exception("HTTPError for url: /v3/movies/550?api_key=SUPERSECRET")

    from affiche.external.poster.provider import FanartClient
    monkeypatch.setattr(FanartClient, "test_connection", boom)

    with pytest.raises(ProviderConnectionError) as exc_info:
        service.test_provider_api_token("fanart", "SUPERSECRET")

    message = str(exc_info.value)
    assert "SUPERSECRET" not in message
    assert "api_key=" not in message
    assert "FANART" in message
