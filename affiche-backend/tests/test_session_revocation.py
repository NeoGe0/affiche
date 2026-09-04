from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import affiche.main as main_module  # noqa: F401  (initialize the package before service imports)
from affiche.app.auth.model.user import User
from affiche.app.auth.service.auth_service import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    AuthService,
)
from affiche.config.env_config import get_auth_secret

class _FakeRepository:

    def __init__(self, user: User):
        self.user = user

    def get_by_username(self, username: str):
        return self.user if self.user and self.user.username == username else None

    def count(self) -> int:
        return 1 if self.user else 0

    def increment_token_version(self, user_id: int):
        self.user = self.user.model_copy(update={"token_version": self.user.token_version + 1})
        return self.user

@pytest.fixture
def service():
    return AuthService(_FakeRepository(
        User(id=1, username="admin", password_hash="x", token_version=0)))

def _legacy_token(username: str = "admin") -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": username, "iat": int(now.timestamp()),
         "exp": int((now + timedelta(seconds=SESSION_TTL_SECONDS)).timestamp())},
        get_auth_secret(), algorithm="HS256")

def test_a_token_is_valid_before_revocation(service):
    token = service.issue_token(service._repository.user)

    assert service.user_from_token(token) is not None

def test_revoking_invalidates_the_token_that_did_it(service):
    token = service.issue_token(service._repository.user)

    assert service.revoke_sessions(token) is True

    assert service.user_from_token(token) is None, "logout left the JWT usable"

def test_revoking_invalidates_every_other_outstanding_token(service):
    phone = service.issue_token(service._repository.user)
    laptop = service.issue_token(service._repository.user)

    service.revoke_sessions(laptop)

    assert service.user_from_token(phone) is None
    assert service.user_from_token(laptop) is None

def test_a_token_issued_after_revocation_works(service):
    service.revoke_sessions(service.issue_token(service._repository.user))

    fresh = service.issue_token(service._repository.user)

    assert service.user_from_token(fresh) is not None

def test_revoking_an_unknown_token_is_a_no_op(service):
    assert service.revoke_sessions("not-a-jwt") is False
    assert service.revoke_sessions(None) is False
    assert service._repository.user.token_version == 0, "a bad token must not bump the counter"

def test_a_forged_version_claim_is_rejected(service):
    token = service.issue_token(service._repository.user)
    service.revoke_sessions(token)
    tampered = token[:-4] + "AAAA"

    assert service.user_from_token(tampered) is None

def test_a_token_minted_before_the_claim_existed_still_validates(service):
    assert service.user_from_token(_legacy_token()) is not None

def test_the_first_logout_after_the_upgrade_invalidates_the_legacy_token(service):
    legacy = _legacy_token()

    service.revoke_sessions(legacy)

    assert service.user_from_token(legacy) is None

def test_logout_endpoint_revokes_and_clears(monkeypatch):
    from affiche.config.dependencies import get_auth_service

    repo = _FakeRepository(User(id=1, username="admin", password_hash="x", token_version=0))
    auth = AuthService(repo)
    main_module.app.dependency_overrides[get_auth_service] = lambda: auth
    try:
        token = auth.issue_token(repo.user)
        with TestClient(main_module.app) as client:
            client.cookies.set(SESSION_COOKIE_NAME, token)
            resp = client.post("/affiche/auth/logout")

        assert resp.status_code == 200
        assert auth.user_from_token(token) is None
    finally:
        main_module.app.dependency_overrides.pop(get_auth_service, None)

def test_logout_succeeds_without_a_valid_session():
    with TestClient(main_module.app) as client:
        assert client.post("/affiche/auth/logout").status_code == 200

        client.cookies.set(SESSION_COOKIE_NAME, "garbage")
        assert client.post("/affiche/auth/logout").status_code == 200

def test_revocation_round_trips_through_the_database(clean_session):
    from affiche.app.auth.service.user_repository import UserRepository

    service = AuthService(UserRepository(clean_session))
    user = service.create_admin("admin", "s3cret-pass")
    token = service.issue_token(user)
    assert service.user_from_token(token) is not None

    service.revoke_sessions(token)

    assert AuthService(UserRepository(clean_session)).user_from_token(token) is None
    assert service.user_from_token(service.issue_token(
        service.authenticate("admin", "s3cret-pass"))) is not None
