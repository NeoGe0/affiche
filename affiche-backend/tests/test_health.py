from unittest.mock import patch

from fastapi.testclient import TestClient

import affiche.main as main_module
from affiche.config.database import database_ok

def test_health_is_public_and_ok_when_the_database_answers():
    with TestClient(main_module.app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "database": "connected"}

def test_health_503s_when_the_database_is_unreachable():
    with TestClient(main_module.app) as client:
        with patch.object(main_module, "database_ok", return_value=False):
            resp = client.get("/health")

    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "database": "error"}

def test_health_does_not_leak_the_failure_detail():
    with TestClient(main_module.app) as client:
        with patch("affiche.config.database.SessionLocal", side_effect=RuntimeError(
                "could not open /data/config/db/affiche.db")):
            resp = client.get("/health")

    assert resp.status_code == 503
    assert "affiche.db" not in resp.text
    assert "/data/config" not in resp.text

def test_health_no_longer_claims_a_task_queue_exists():
    with TestClient(main_module.app) as client:
        assert "celery" not in client.get("/health").text

def test_database_ok_reports_failure_instead_of_raising():
    with patch("affiche.config.database.SessionLocal", side_effect=RuntimeError("boom")):
        assert database_ok() is False

def test_database_ok_is_true_against_the_real_database():
    assert database_ok() is True

def test_settings_info_reports_the_real_database_state(authenticated_app):
    with TestClient(authenticated_app) as client:
        assert client.get("/affiche/settings/info").json()["database"] == "connected"

        with patch("affiche.api.routers.settings.database_ok", return_value=False):
            assert client.get("/affiche/settings/info").json()["database"] == "error"
