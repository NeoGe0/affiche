from fastapi.testclient import TestClient

from affiche.main import app

def test_business_routes_require_a_session():
    with TestClient(app) as client:
        for path in (
            "/affiche/media-servers/",
            "/affiche/media-servers/1/libraries",
            "/affiche/config/tmdb",
            "/affiche/settings/info",
            "/affiche/tasks/",
        ):
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should be gated, got {resp.status_code}"
            assert resp.json()["detail"] == "Not authenticated"

def test_public_routes_are_not_gated():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 200
        assert client.get("/affiche/auth/status").status_code != 401
