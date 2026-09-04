import pytest

from affiche.app.auth.service.auth_service import AuthService, AuthError
from affiche.app.auth.service.user_repository import UserRepository

def _service(session) -> AuthService:
    return AuthService(UserRepository(session))

def test_has_admin_false_when_empty(clean_session):
    assert _service(clean_session).has_admin() is False

def test_create_admin_and_authenticate(clean_session):
    svc = _service(clean_session)
    user = svc.create_admin("admin", "s3cret-pass")

    assert user.username == "admin"
    assert user.password_hash != "s3cret-pass"
    assert user.password_hash.startswith("$2")
    assert svc.has_admin() is True

def test_authenticate_success_and_failure(clean_session):
    svc = _service(clean_session)
    svc.create_admin("admin", "s3cret-pass")

    assert svc.authenticate("admin", "s3cret-pass") is not None
    assert svc.authenticate("admin", "wrong") is None
    assert svc.authenticate("ghost", "s3cret-pass") is None

def test_create_admin_rejects_second_account(clean_session):
    svc = _service(clean_session)
    svc.create_admin("admin", "s3cret-pass")

    with pytest.raises(AuthError):
        svc.create_admin("second", "another-pass")

def test_create_admin_validates_input(clean_session):
    svc = _service(clean_session)
    with pytest.raises(AuthError):
        svc.create_admin("", "pass")
    with pytest.raises(AuthError):
        svc.create_admin("admin", "")

def test_token_round_trip(clean_session):
    svc = _service(clean_session)
    user = svc.create_admin("admin", "s3cret-pass")

    token = svc.issue_token(user)
    resolved = svc.user_from_token(token)
    assert resolved is not None
    assert resolved.username == "admin"

def test_invalid_token_returns_none(clean_session):
    svc = _service(clean_session)
    svc.create_admin("admin", "s3cret-pass")

    assert svc.user_from_token("not-a-jwt") is None
    assert svc.user_from_token("") is None
    assert svc.user_from_token(None) is None

def test_long_password_does_not_raise(clean_session):
    svc = _service(clean_session)
    long_pw = "a" * 200
    svc.create_admin("admin", long_pw)
    assert svc.authenticate("admin", long_pw) is not None
