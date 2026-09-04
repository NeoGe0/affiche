import pytest
from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche.app.auth.model.user import User, UserRole
from affiche.app.auth.service.auth_service import AuthError, AuthService
from affiche.app.auth.service.user_repository import UserRepository
from affiche.config.database import SessionLocal, init_db
from affiche.config.dependencies import get_current_user

ADMIN = User(id=1, username="boss", password_hash="x", role=UserRole.ADMIN)
OPERATOR = User(id=2, username="helper", password_hash="x", role=UserRole.OPERATOR)

@pytest.fixture
def as_operator():
    from affiche.main import app
    app.dependency_overrides[get_current_user] = lambda: OPERATOR
    yield app
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def seeded():
    from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity
    from affiche.app.mediaserver.library.connector.library_entity import LibraryEntity
    from affiche.app.mediaserver.model.media_server import MediaServerType

    init_db()
    session = SessionLocal()
    try:
        server = MediaServerEntity(name="Probe", type=MediaServerType.PLEX, url="http://x",
                                   token="t", enabled=True)
        session.add(server)
        session.flush()
        library = LibraryEntity(media_server_id=server.id, external_id="1", name="Films",
                                type="movie", language="en", enabled=True)
        session.add(library)
        session.commit()
        ids = (server.id, library.id)
    finally:
        session.close()
    return ids

@pytest.fixture
def accounts():
    init_db()
    session = SessionLocal()
    from affiche.app.auth.connector.user_entity import UserEntity
    for entity in session.query(UserEntity).all():
        session.delete(entity)
    session.commit()
    try:
        yield AuthService(UserRepository(session))
    finally:
        session.close()

def _call(client: TestClient, method: str, path: str, ids=(1, 1)):
    path = path.format(server=ids[0], library=ids[1])
    if method in ("get", "delete"):
        return getattr(client, method)(path)
    return getattr(client, method)(path, json={})

ADMIN_ONLY = [
    ("post", "/affiche/media-servers/"),
    ("patch", "/affiche/media-servers/{server}/language-order"),
    ("get", "/affiche/media-servers/{server}/available-libraries"),
    ("get", "/affiche/config"),
    ("delete", "/affiche/media-servers/{server}/libraries/{library}"),
    ("patch", "/affiche/media-servers/{server}/libraries/{library}/settings"),
    ("put", "/affiche/settings/"),
    ("put", "/affiche/settings/poster-config"),
    ("post", "/affiche/style-profiles"),
    ("get", "/affiche/auth/users"),
    ("post", "/affiche/auth/users"),
    ("patch", "/affiche/auth/users/{library}"),
]

@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_an_operator_is_refused_the_configuration_surface(as_operator, seeded, method, path):
    with TestClient(as_operator) as client:
        resp = _call(client, method, path, seeded)

    assert resp.status_code == 403, f"{method.upper()} {path} answered {resp.status_code}"
    assert resp.json()["detail"] == "Administrator access required"

def test_the_refusal_is_403_not_401(as_operator):
    with TestClient(as_operator) as client:
        assert client.get("/affiche/config").status_code == 403

OPERATOR_ALLOWED = [
    ("get", "/affiche/dashboard/stats"),
    ("get", "/affiche/search?q=x"),
    ("get", "/affiche/settings/info"),
    ("get", "/affiche/settings/poster-config"),
    ("get", "/affiche/style-profiles"),
    ("get", "/affiche/tasks/"),
    ("get", "/affiche/media-servers/"),
    ("get", "/affiche/media-servers/{server}"),
    ("get", "/affiche/media-servers/{server}/libraries"),
    ("get", "/affiche/media-servers/{server}/libraries/{library}/settings"),
    ("post", "/affiche/media-servers/{server}/libraries/{library}/sync"),
    ("post", "/affiche/media-servers/{server}/libraries/{library}/posters/sync"),
    ("post", "/affiche/media-servers/{server}/libraries/{library}/posters/reset"),
    ("post", "/affiche/media-servers/{server}/libraries/{library}/posters/upload"),
]

@pytest.mark.parametrize("method,path", OPERATOR_ALLOWED)
def test_an_operator_keeps_the_working_surface(as_operator, seeded, method, path):
    with TestClient(as_operator) as client:
        resp = _call(client, method, path, seeded)

    assert resp.status_code != 403, f"{method.upper()} {path} was refused"

def test_an_admin_is_refused_nothing_an_operator_is(authenticated_app, seeded):
    ordered = sorted(ADMIN_ONLY, key=lambda entry: entry[0] == "delete")
    with TestClient(authenticated_app) as client:
        for method, path in ordered:
            resp = _call(client, method, path, seeded)
            assert resp.status_code != 403, f"{method.upper()} {path} refused an admin"

def test_a_new_account_is_an_operator_unless_asked_otherwise(accounts):
    user = accounts.create_user("helper", "a-good-password", UserRole.OPERATOR)

    assert user.role == UserRole.OPERATOR

def test_a_new_account_can_sign_in(accounts):
    accounts.create_user("helper", "a-good-password", UserRole.OPERATOR)

    assert accounts.authenticate("helper", "a-good-password") is not None

def test_a_duplicate_username_is_refused(accounts):
    accounts.create_user("helper", "a-good-password", UserRole.OPERATOR)

    with pytest.raises(AuthError):
        accounts.create_user("helper", "another-password", UserRole.OPERATOR)

def test_a_short_password_is_refused(accounts):
    with pytest.raises(AuthError):
        accounts.create_user("helper", "short", UserRole.OPERATOR)

def test_creating_an_account_is_not_first_run_setup(accounts):
    accounts.create_admin("boss", "a-good-password")

    accounts.create_user("helper", "a-good-password", UserRole.OPERATOR)

    assert len(accounts.list_users()) == 2

def test_an_admin_cannot_delete_their_own_account(accounts):
    boss = accounts.create_admin("boss", "a-good-password")

    with pytest.raises(AuthError):
        accounts.delete_user(boss.id, acting_user=boss)

def test_the_last_admin_cannot_be_deleted(accounts):
    boss = accounts.create_admin("boss", "a-good-password")
    second = accounts.create_user("second", "a-good-password", UserRole.ADMIN)

    accounts.delete_user(boss.id, acting_user=second)

    with pytest.raises(AuthError):
        accounts.delete_user(second.id, acting_user=second)

def test_an_admin_can_change_another_account_s_role(accounts):
    boss = accounts.create_admin("boss", "a-good-password")
    helper = accounts.create_user("helper", "a-good-password", UserRole.OPERATOR)

    promoted = accounts.set_role(helper.id, UserRole.ADMIN, acting_user=boss)

    assert promoted.role == UserRole.ADMIN
    assert accounts.list_users()[1].role == UserRole.ADMIN

def test_an_admin_can_be_demoted_by_another_admin(accounts):
    boss = accounts.create_admin("boss", "a-good-password")
    second = accounts.create_user("second", "a-good-password", UserRole.ADMIN)

    assert accounts.set_role(second.id, UserRole.OPERATOR, acting_user=boss).role \
        == UserRole.OPERATOR

def test_an_admin_cannot_change_their_own_role(accounts):
    boss = accounts.create_admin("boss", "a-good-password")

    with pytest.raises(AuthError):
        accounts.set_role(boss.id, UserRole.OPERATOR, acting_user=boss)

    assert accounts.list_users()[0].role == UserRole.ADMIN

def test_the_last_admin_cannot_be_demoted_because_only_they_could_do_it(accounts):
    boss = accounts.create_admin("boss", "a-good-password")
    helper = accounts.create_user("helper", "a-good-password", UserRole.OPERATOR)

    with pytest.raises(AuthError):
        accounts.set_role(boss.id, UserRole.OPERATOR, acting_user=boss)

    assert accounts.set_role(helper.id, UserRole.ADMIN, acting_user=boss).role == UserRole.ADMIN

def test_changing_a_role_on_a_missing_account_is_refused(accounts):
    boss = accounts.create_admin("boss", "a-good-password")

    with pytest.raises(AuthError):
        accounts.set_role(4321, UserRole.ADMIN, acting_user=boss)

def test_a_demoted_admin_loses_the_admin_surface_on_their_next_request(accounts):
    boss = accounts.create_admin("boss", "a-good-password")
    second = accounts.create_user("second", "a-good-password", UserRole.ADMIN)
    token = accounts.issue_token(second)

    accounts.set_role(second.id, UserRole.OPERATOR, acting_user=boss)

    assert accounts.user_from_token(token).role == UserRole.OPERATOR

def test_an_operator_can_be_deleted(accounts):
    boss = accounts.create_admin("boss", "a-good-password")
    helper = accounts.create_user("helper", "a-good-password", UserRole.OPERATOR)

    accounts.delete_user(helper.id, acting_user=boss)

    assert [u.username for u in accounts.list_users()] == ["boss"]

def test_the_listing_carries_no_password_material(authenticated_app, accounts):
    accounts.create_admin("boss", "a-secret-password")

    with TestClient(authenticated_app) as client:
        body = client.get("/affiche/auth/users").json()

    assert "a-secret-password" not in str(body)
    assert all("password_hash" not in account for account in body)
    assert body[0]["role"] == "ADMIN"

def _with_webhook_token(server_id: int, token: str) -> None:
    from affiche.app.mediaserver.connector.media_server_entity import MediaServerEntity
    session = SessionLocal()
    try:
        entity = session.get(MediaServerEntity, server_id)
        entity.webhook_enabled = True
        entity.webhook_token = token
        session.commit()
    finally:
        session.close()

def test_an_operator_reads_the_server_list_without_its_webhook_token(as_operator, seeded):
    server_id = seeded[0]
    _with_webhook_token(server_id, "operator-probe-token")

    with TestClient(as_operator) as client:
        listed = client.get("/affiche/media-servers/")
        single = client.get(f"/affiche/media-servers/{server_id}")

    assert listed.status_code == 200
    rows = {row["id"]: row for row in listed.json()}
    assert server_id in rows
    assert rows[server_id]["webhook_token"] is None
    assert single.status_code == 200
    assert single.json()["webhook_token"] is None

def test_an_admin_still_sees_the_webhook_token(authenticated_app, seeded):
    server_id = seeded[0]
    _with_webhook_token(server_id, "admin-probe-token")

    with TestClient(authenticated_app) as client:
        resp = client.get(f"/affiche/media-servers/{server_id}")

    assert resp.json()["webhook_token"] == "admin-probe-token"
