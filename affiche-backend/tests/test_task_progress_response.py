from fastapi.testclient import TestClient

import affiche.main as main_module  # noqa: F401
from affiche.config.dependencies import container

PROGRESS = {"current": 12, "total": 100, "message": "Generating posters — Movies"}

def _running_task(task_name="poster_sync_1", resource="ms:1:lib:1"):
    service = container.async_task_service
    task_id, _ = service._register_task(task_name, blocking=True, resource=resource)
    service.tasks[task_id]["status"] = "running"
    service._report_progress(task_id, task_name, **PROGRESS)
    return service, task_id

def _forget(service, task_id):
    service.tasks.pop(task_id, None)
    service.cancel_events.pop(task_id, None)

def test_running_blocking_task_reports_its_progress(authenticated_app):
    service, task_id = _running_task()
    try:
        with TestClient(authenticated_app) as client:
            resp = client.get("/affiche/tasks/blocking/current")

        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == task_id
        assert body["progress"] == PROGRESS
    finally:
        _forget(service, task_id)

def test_task_status_reports_its_progress(authenticated_app):
    service, task_id = _running_task(task_name="poster_sync_2", resource="ms:1:lib:2")
    try:
        with TestClient(authenticated_app) as client:
            resp = client.get(f"/affiche/tasks/{task_id}")

        assert resp.status_code == 200
        assert resp.json()["progress"] == PROGRESS
    finally:
        _forget(service, task_id)

def test_progress_is_null_for_a_task_that_never_reported(authenticated_app):
    service = container.async_task_service
    task_id, _ = service._register_task("library_sync_9", blocking=True, resource="ms:9:*")
    service.tasks[task_id]["status"] = "running"
    try:
        with TestClient(authenticated_app) as client:
            resp = client.get("/affiche/tasks/blocking/current")

        assert resp.status_code == 200
        assert resp.json()["progress"] is None
    finally:
        _forget(service, task_id)
