import threading
from datetime import datetime, timedelta, timezone

import pytest

from affiche.app.asynch.async_task_service import AsyncTaskService, TaskConflictError
from affiche.app.asynch.auto_pickup import dispatch_library_pickup
from affiche.app.asynch.auto_sync_scheduler import _is_due
from affiche.app.mediaserver.library.settings.model.library_settings import AutoPickupAction

def test_is_due_when_never_synced():
    assert _is_due(None, 360, datetime(2026, 7, 11, 12, 0)) is True

def test_is_due_when_interval_elapsed():
    now = datetime(2026, 7, 11, 12, 0)
    assert _is_due(now - timedelta(minutes=361), 360, now) is True

def test_not_due_within_interval():
    now = datetime(2026, 7, 11, 12, 0)
    assert _is_due(now - timedelta(minutes=10), 360, now) is False

def test_is_due_compares_a_naive_watermark_against_an_aware_now():
    now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    stored = datetime(2026, 7, 11, 5, 0)

    assert _is_due(stored, 360, now) is True
    assert _is_due(stored, 600, now) is False

def test_is_due_handles_an_aware_watermark_too():
    now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    stored = datetime(2026, 7, 11, 5, 0, tzinfo=timezone.utc)

    assert _is_due(stored, 360, now) is True
    assert _is_due(stored, 600, now) is False

class _RecordingTaskService:
    def __init__(self):
        self.calls = []

    def submit_detached_task(self, task_func, task_name, blocking=False, resource=None, **kwargs):
        self.calls.append({"task_name": task_name, "blocking": blocking, "resource": resource})
        return "task-id", "pending"

def test_dispatch_sync_action_maps_to_library_sync():
    svc = _RecordingTaskService()
    dispatch_library_pickup(svc, media_server_id=2, library_id=5, action=AutoPickupAction.SYNC)
    assert svc.calls[0]["task_name"] == "library_sync_2_5"
    assert svc.calls[0]["resource"] == "ms:2:lib:5"
    assert svc.calls[0]["blocking"] is True

def test_dispatch_generate_and_upload_map_to_poster_sync():
    svc = _RecordingTaskService()
    dispatch_library_pickup(svc, 2, 5, AutoPickupAction.GENERATE)
    dispatch_library_pickup(svc, 2, 5, AutoPickupAction.UPLOAD)
    assert svc.calls[0]["task_name"] == "poster_sync_5"
    assert svc.calls[1]["task_name"] == "poster_sync_5"
    assert all(c["resource"] == "ms:2:lib:5" for c in svc.calls)

def test_dispatch_returns_none_on_conflict():
    class _Conflicting:
        def submit_detached_task(self, **kwargs):
            raise TaskConflictError("running-id", kwargs.get("resource"))
    assert dispatch_library_pickup(_Conflicting(), 1, 1, AutoPickupAction.SYNC) is None

def test_submit_detached_task_dedup_and_conflict():
    service = AsyncTaskService()
    started = threading.Event()
    release = threading.Event()

    def blocker(cancel_check=None):
        started.set()
        release.wait(timeout=5)

    tid1, status1 = service.submit_detached_task(
        blocker, task_name="job_a", blocking=True, resource="ms:1:*")
    assert status1 == "pending"
    assert started.wait(timeout=5)

    tid2, status2 = service.submit_detached_task(
        blocker, task_name="job_a", blocking=True, resource="ms:1:*")
    assert tid2 == tid1
    assert status2 == "running"

    with pytest.raises(TaskConflictError):
        service.submit_detached_task(
            blocker, task_name="job_b", blocking=True, resource="ms:1:lib:9")

    release.set()
