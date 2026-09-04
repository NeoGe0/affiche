from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401

def _create(client, name: str, enabled: bool = True):
    return client.post("/affiche/config/", json={
        "name": name, "type": "PROVIDER", "url": "https://api.example.com",
        "token": f"{name}-token", "enabled": enabled,
    })

def test_find_returns_only_the_configured_providers(authenticated_app):
    with TestClient(authenticated_app) as client:
        _create(client, "tmdb")
        _create(client, "fanart")

        resp = client.get("/affiche/config", params={"type": "PROVIDER"})

        assert resp.status_code == 200
        assert {c["name"] for c in resp.json()} == {"tmdb", "fanart"}

def test_find_never_returns_a_token(authenticated_app):
    with TestClient(authenticated_app) as client:
        _create(client, "tmdb")

        configs = client.get("/affiche/config", params={"type": "PROVIDER"}).json()
        config = next(c for c in configs if c["name"] == "tmdb")

        assert "token" not in config
        assert config["configured"] is True
        assert config["token_hint"] == "oken"

def test_delete_removes_it_from_the_listing(authenticated_app):
    with TestClient(authenticated_app) as client:
        _create(client, "tmdb")
        _create(client, "fanart")

        assert client.delete("/affiche/config/tmdb").status_code == 204

        names = {c["name"] for c in client.get("/affiche/config").json()}
        assert "tmdb" not in names and "fanart" in names
        assert client.get("/affiche/config/tmdb").json() is None

def test_deleting_an_unknown_provider_is_a_404(authenticated_app):
    with TestClient(authenticated_app) as client:
        assert client.delete("/affiche/config/nope").status_code == 404

def test_recreating_after_a_delete_starts_from_no_token(authenticated_app):
    with TestClient(authenticated_app) as client:
        _create(client, "tmdb")
        client.delete("/affiche/config/tmdb")

        resp = client.post("/affiche/config/", json={
            "name": "tmdb", "type": "PROVIDER", "url": "https://api.example.com", "enabled": True,
        })

        assert resp.status_code == 200
        assert resp.json()["configured"] is False
