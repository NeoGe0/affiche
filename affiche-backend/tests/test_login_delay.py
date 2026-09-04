import asyncio
import inspect
import time
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

import affiche.api.routers.auth as auth_router
import affiche.main as main_module
from affiche.app.auth.model.user import User
from affiche.config.dependencies import get_auth_service

TEST_DELAY = 0.4

@pytest.fixture
def stub_auth(monkeypatch):
    monkeypatch.setattr(auth_router, "FAILED_LOGIN_DELAY_SECONDS", TEST_DELAY)

    service = MagicMock()
    user = User(id=1, username="admin", password_hash="x")
    service.authenticate.side_effect = (
        lambda username, password: user if (username, password) == ("admin", "right") else None
    )
    service.issue_token.return_value = "token"

    main_module.app.dependency_overrides[get_auth_service] = lambda: service
    yield service
    main_module.app.dependency_overrides.pop(get_auth_service, None)

def _login(client, username: str, password: str):
    started = time.monotonic()
    resp = client.post("/affiche/auth/login", json={"username": username, "password": password})
    return resp, time.monotonic() - started

def test_a_wrong_password_is_delayed(stub_auth):
    with TestClient(main_module.app) as client:
        resp, elapsed = _login(client, "admin", "wrong")

    assert resp.status_code == 401
    assert elapsed >= TEST_DELAY

def test_a_successful_login_is_not_delayed(stub_auth):
    with TestClient(main_module.app) as client:
        resp, elapsed = _login(client, "admin", "right")

    assert resp.status_code == 200
    assert elapsed < TEST_DELAY, "the delay must only apply to failures"

def test_an_unknown_username_is_delayed_the_same_as_a_wrong_password(stub_auth):
    with TestClient(main_module.app) as client:
        _, unknown_user = _login(client, "nobody", "whatever")
        _, wrong_password = _login(client, "admin", "wrong")

    assert unknown_user >= TEST_DELAY
    assert wrong_password >= TEST_DELAY

def test_the_failure_message_does_not_say_which_half_was_wrong(stub_auth):
    with TestClient(main_module.app) as client:
        unknown = client.post("/affiche/auth/login",
                              json={"username": "nobody", "password": "x"}).json()
        wrong = client.post("/affiche/auth/login",
                            json={"username": "admin", "password": "wrong"}).json()

    assert unknown == wrong == {"detail": "Invalid username or password"}

def test_login_is_a_coroutine_so_the_delay_holds_no_worker_thread():
    assert inspect.iscoroutinefunction(auth_router.login)

def test_concurrent_failed_logins_do_not_serialise(stub_auth):
    attempts = 12

    async def hammer():
        transport = httpx.ASGITransport(app=main_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            started = time.monotonic()
            responses = await asyncio.gather(*[
                client.post("/affiche/auth/login",
                            json={"username": "admin", "password": "wrong"})
                for _ in range(attempts)
            ])
            return responses, time.monotonic() - started

    responses, elapsed = asyncio.run(hammer())

    assert all(r.status_code == 401 for r in responses)
    assert elapsed >= TEST_DELAY, "each attempt must still be delayed"
    assert elapsed < TEST_DELAY * attempts / 2, (
        f"{attempts} concurrent failures took {elapsed:.2f}s — they are serialising, so the "
        f"delay is blocking the event loop or a worker thread")
