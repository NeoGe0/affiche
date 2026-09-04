import pytest
from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche import cli
from affiche.app.auth.service.auth_service import (
    AuthError,
    AuthService,
    MIN_PASSWORD_LENGTH,
    SESSION_COOKIE_NAME,
)
from affiche.app.auth.service.user_repository import UserRepository
from affiche.config.database import SessionLocal, init_db

USERNAME = "admin"
ORIGINAL_PASSWORD = "original-password"
CHOSEN_PASSWORD = "a-password-i-picked"

@pytest.fixture
def account():
    init_db()
    session = SessionLocal()
    try:
        from affiche.app.auth.connector.user_entity import UserEntity
        for entity in session.query(UserEntity).all():
            session.delete(entity)
        session.commit()
        AuthService(UserRepository(session)).create_admin(USERNAME, ORIGINAL_PASSWORD)
    finally:
        session.close()

def _reset(username: str | None = None) -> str:
    session = SessionLocal()
    try:
        return AuthService(UserRepository(session)).reset_password(username)[1]
    finally:
        session.close()

def _login(client: TestClient, password: str, username: str = USERNAME):
    return client.post("/affiche/auth/login", json={"username": username, "password": password})

def test_the_generated_password_signs_the_account_in(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        assert _login(client, temporary).status_code == 200

def test_the_old_password_stops_working(account):
    _reset()

    with TestClient(main_module.app) as client:
        assert _login(client, ORIGINAL_PASSWORD).status_code == 401

def test_two_resets_do_not_produce_the_same_password(account):
    assert _reset() != _reset()

def test_it_signs_every_existing_session_out(account):
    with TestClient(main_module.app) as client:
        _login(client, ORIGINAL_PASSWORD)
        assert client.get("/affiche/auth/status").json()["authenticated"] is True

        _reset()

        assert client.get("/affiche/auth/status").json()["authenticated"] is False

def test_resetting_an_unknown_account_is_refused(account):
    with pytest.raises(AuthError):
        _reset("nobody")

def test_the_cli_reports_the_password_on_stdout(account, capsys):
    exit_code = cli.main(["reset-password"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert USERNAME in out
    password = out.split("Temporary password:")[1].split("\n")[0].strip()
    with TestClient(main_module.app) as client:
        assert _login(client, password).status_code == 200

def test_the_cli_fails_loudly_when_there_is_no_account():
    init_db()
    session = SessionLocal()
    try:
        from affiche.app.auth.connector.user_entity import UserEntity
        for entity in session.query(UserEntity).all():
            session.delete(entity)
        session.commit()
    finally:
        session.close()

    assert cli.main(["reset-password"]) == 1

def test_the_session_is_told_a_change_is_required(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        body = _login(client, temporary).json()
        assert body["password_change_required"] is True
        assert client.get("/affiche/auth/status").json()["password_change_required"] is True

def test_the_rest_of_the_app_is_refused_until_it_happens(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        _login(client, temporary)

        resp = client.get("/affiche/media-servers/")

        assert resp.status_code == 403
        assert resp.json()["detail"] == "Password change required"

def test_changing_it_reopens_the_app(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        _login(client, temporary)

        changed = client.post("/affiche/auth/password",
                              json={"current_password": temporary,
                                    "new_password": CHOSEN_PASSWORD})

        assert changed.status_code == 200, changed.text
        assert changed.json()["password_change_required"] is False
        assert client.get("/affiche/media-servers/").status_code == 200

def test_the_caller_stays_signed_in_afterwards(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        _login(client, temporary)
        before = client.cookies[SESSION_COOKIE_NAME]

        client.post("/affiche/auth/password",
                    json={"current_password": temporary, "new_password": CHOSEN_PASSWORD})

        assert client.cookies[SESSION_COOKIE_NAME] != before
        assert client.get("/affiche/auth/status").json()["authenticated"] is True

def test_the_new_password_is_the_one_that_works(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        _login(client, temporary)
        client.post("/affiche/auth/password",
                    json={"current_password": temporary, "new_password": CHOSEN_PASSWORD})
        client.post("/affiche/auth/logout")

        assert _login(client, temporary).status_code == 401
        assert _login(client, CHOSEN_PASSWORD).status_code == 200

def test_other_sessions_are_signed_out_by_the_change(account):
    temporary = _reset()

    with TestClient(main_module.app) as changing, TestClient(main_module.app) as other:
        _login(changing, temporary)
        _login(other, temporary)

        changing.post("/affiche/auth/password",
                      json={"current_password": temporary, "new_password": CHOSEN_PASSWORD})

        assert other.get("/affiche/auth/status").json()["authenticated"] is False

def test_the_current_password_is_required_even_when_it_is_temporary(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        _login(client, temporary)

        resp = client.post("/affiche/auth/password",
                           json={"current_password": "not-it", "new_password": CHOSEN_PASSWORD})

        assert resp.status_code == 400
        assert client.get("/affiche/media-servers/").status_code == 403

def test_a_too_short_password_is_refused(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        _login(client, temporary)

        resp = client.post("/affiche/auth/password",
                           json={"current_password": temporary,
                                 "new_password": "x" * (MIN_PASSWORD_LENGTH - 1)})

        assert resp.status_code == 400
        assert str(MIN_PASSWORD_LENGTH) in resp.json()["detail"]

def test_reusing_the_temporary_password_is_refused(account):
    temporary = _reset()

    with TestClient(main_module.app) as client:
        _login(client, temporary)

        resp = client.post("/affiche/auth/password",
                           json={"current_password": temporary, "new_password": temporary})

        assert resp.status_code == 400

def test_changing_a_password_without_a_session_is_refused(account):
    with TestClient(main_module.app) as client:
        resp = client.post("/affiche/auth/password",
                           json={"current_password": ORIGINAL_PASSWORD,
                                 "new_password": CHOSEN_PASSWORD})

        assert resp.status_code == 401

def test_a_normal_account_can_change_its_password_too(account):
    with TestClient(main_module.app) as client:
        _login(client, ORIGINAL_PASSWORD)

        resp = client.post("/affiche/auth/password",
                           json={"current_password": ORIGINAL_PASSWORD,
                                 "new_password": CHOSEN_PASSWORD})

        assert resp.status_code == 200
        assert resp.json()["password_change_required"] is False
