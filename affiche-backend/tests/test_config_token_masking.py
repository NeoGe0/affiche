from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche.api.schemas.api_schemas import token_hint

FULL_TOKEN = "abcdefghijklmnop1234"

def _save(client, name: str, **overrides) -> dict:
    payload = {"name": name, "type": "PROVIDER", "url": f"https://api.{name}.com",
               "enabled": True}
    payload.update(overrides)
    resp = client.post("/affiche/config/", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()

def _get(client, name: str) -> dict:
    resp = client.get(f"/affiche/config/{name}")
    assert resp.status_code == 200, resp.text
    return resp.json()

def test_hint_is_the_tail_of_the_token():
    assert token_hint("abcdefghijklmnop1234") == "1234"

def test_no_hint_when_nothing_is_stored():
    assert token_hint("") is None
    assert token_hint(None) is None

def test_no_hint_for_a_token_short_enough_to_be_revealed_by_it():
    assert token_hint("abcd") is None
    assert token_hint("abc") is None
    assert token_hint("abcde") == "bcde"

def test_the_token_is_never_returned(authenticated_app):
    with TestClient(authenticated_app) as client:
        _save(client, "tmdb", token=FULL_TOKEN)

        body = _get(client, "tmdb")

        assert FULL_TOKEN not in str(body)
        assert "token" not in body or body.get("token") is None
        assert body["configured"] is True
        assert body["token_hint"] == "1234"

def test_a_provider_with_no_token_reads_as_unconfigured(authenticated_app):
    with TestClient(authenticated_app) as client:
        _save(client, "tvmaze", token="")

        body = _get(client, "tvmaze")

        assert body["configured"] is False
        assert body["token_hint"] is None

def test_an_unknown_key_is_still_null(authenticated_app):
    with TestClient(authenticated_app) as client:
        assert client.get("/affiche/config/nonexistent").json() is None

def test_the_save_response_does_not_leak_it_either(authenticated_app):
    with TestClient(authenticated_app) as client:
        body = _save(client, "fanart", token=FULL_TOKEN)

        assert FULL_TOKEN not in str(body)
        assert body["configured"] is True

def test_omitting_the_token_keeps_the_stored_one(authenticated_app):
    with TestClient(authenticated_app) as client:
        _save(client, "tvdb", token=FULL_TOKEN)

        _save(client, "tvdb", enabled=False)

        body = _get(client, "tvdb")
        assert body["configured"] is True, "the stored token was wiped by an unrelated save"
        assert body["token_hint"] == "1234"
        assert body["enabled"] is False

def test_a_null_token_also_keeps_the_stored_one(authenticated_app):
    with TestClient(authenticated_app) as client:
        _save(client, "mediux", token=FULL_TOKEN)

        _save(client, "mediux", token=None, enabled=False)

        assert _get(client, "mediux")["token_hint"] == "1234"

def test_a_new_token_replaces_the_stored_one(authenticated_app):
    with TestClient(authenticated_app) as client:
        _save(client, "tmdb", token=FULL_TOKEN)

        _save(client, "tmdb", token="zzzzzzzzzzzzzzzz9999")

        assert _get(client, "tmdb")["token_hint"] == "9999"

def test_an_explicit_empty_token_clears_it(authenticated_app):
    with TestClient(authenticated_app) as client:
        _save(client, "fanart", token=FULL_TOKEN)

        _save(client, "fanart", token="")

        assert _get(client, "fanart")["configured"] is False

def test_omitting_the_token_on_a_brand_new_config_is_not_an_error(authenticated_app):
    with TestClient(authenticated_app) as client:
        body = _save(client, "tvmaze", enabled=True)

        assert body["configured"] is False
        assert body["enabled"] is True

def test_the_stored_token_still_reaches_the_provider_factory(authenticated_app):
    from affiche.app.service_configuration.service.configuration_repository import (
        ConfigurationRepository,
    )
    from affiche.app.service_configuration.service.service_configuration_service import (
        ServiceConfigurationService,
    )
    from affiche.config.database import SessionLocal

    with TestClient(authenticated_app) as client:
        _save(client, "tmdb", token=FULL_TOKEN)

    session = SessionLocal()
    try:
        config = ServiceConfigurationService(ConfigurationRepository(session)).get_config("tmdb")
        assert config.token == FULL_TOKEN
    finally:
        session.close()
