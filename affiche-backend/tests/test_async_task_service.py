from unittest.mock import MagicMock

import pytest

from affiche.app.asynch.async_task_service import (
    AsyncTaskService,
    TaskConflictError,
    report_task_progress,
    progress_segment,
    _current_progress,
)

def _noop(cancel_check=None):
    return None

def _svc():
    return AsyncTaskService(), MagicMock()

def test_same_name_dedup_rides_the_running_task():
    svc, bg = _svc()
    tid1, st1 = svc.submit_task(bg, _noop, "library_sync_1")
    tid2, st2 = svc.submit_task(bg, _noop, "library_sync_1")

    assert st1 == "pending"
    assert (tid2, st2) == (tid1, "running")
    assert len(svc.tasks) == 1

def test_blocking_conflict_same_server_wildcard():
    svc, bg = _svc()
    svc.submit_task(bg, _noop, "library_sync_1", blocking=True, resource="ms:1:*")

    with pytest.raises(TaskConflictError):
        svc.submit_task(bg, _noop, "poster_sync_3", blocking=True, resource="ms:1:lib:3")

def test_blocking_allows_different_server_and_different_library():
    svc, bg = _svc()
    svc.submit_task(bg, _noop, "poster_sync_3", blocking=True, resource="ms:1:lib:3")

    _, st_lib = svc.submit_task(bg, _noop, "poster_sync_5", blocking=True, resource="ms:1:lib:5")
    _, st_srv = svc.submit_task(bg, _noop, "poster_sync_9", blocking=True, resource="ms:2:lib:9")

    assert st_lib == "pending"
    assert st_srv == "pending"

def test_cleanup_evicts_only_terminal_tasks():
    svc, _ = _svc()
    svc.max_tasks = 2
    svc.tasks["a"] = {"status": "completed", "created_at": "1"}
    svc.tasks["b"] = {"status": "running", "created_at": "2"}
    svc.tasks["c"] = {"status": "completed", "created_at": "3"}

    svc._cleanup_old_tasks()

    assert "b" in svc.tasks
    assert len(svc.tasks) == 2
    assert "a" not in svc.tasks

def test_running_records_survive_even_over_cap():
    svc, _ = _svc()
    svc.max_tasks = 1
    svc.tasks["a"] = {"status": "running", "created_at": "1"}
    svc.tasks["b"] = {"status": "running", "created_at": "2"}

    svc._cleanup_old_tasks()

    assert len(svc.tasks) == 2

def test_cancel_running_task_sets_status_and_event():
    svc, bg = _svc()
    tid, _ = svc.submit_task(bg, _noop, "library_sync_1")

    assert svc.cancel_task(tid) is True
    assert svc.tasks[tid]["status"] == "cancelled"
    assert svc.is_cancelled(tid) is True

def test_report_task_progress_is_noop_without_a_running_task():
    report_task_progress(1, 2, "x")

def test_run_task_binds_reporter_so_nested_code_records_progress():
    svc, bg = _svc()
    tid, _ = svc.submit_task(bg, _noop, "poster_sync_1")

    captured = {}

    def task_func(cancel_check=None):
        report_task_progress(3, 10, "Generating")
        captured["progress"] = dict(svc.tasks[tid]["progress"])

    svc._run_task(tid, task_func)

    assert captured["progress"] == {"current": 30, "total": 100, "message": "Generating"}
    assert svc.tasks[tid]["status"] == "completed"
    assert _current_progress.get() is None

def test_progress_segment_scales_and_composes():
    reported = []
    token = _current_progress.set(lambda cur, total, msg=None: reported.append(cur))
    try:
        with progress_segment(0, 0.5):
            report_task_progress(1, 5)
        with progress_segment(0.5, 0.5):
            report_task_progress(1, 5)
            with progress_segment(0.0, 0.4):
                report_task_progress(1, 4)
    finally:
        _current_progress.reset(token)

    assert reported == [10, 60, 55]

def test_report_progress_ignores_tasks_that_are_no_longer_active():
    svc, _ = _svc()
    svc.tasks["z"] = {"status": "completed", "task_name": "poster_sync_1", "created_at": "1"}

    svc._report_progress("z", "poster_sync_1", 1, 2, "x")

    assert "progress" not in svc.tasks["z"]

def test_cancel_does_not_clobber_completed_task():
    svc, bg = _svc()
    tid, _ = svc.submit_task(bg, _noop, "library_sync_1")
    svc.tasks[tid]["status"] = "completed"

    assert svc.cancel_task(tid) is False
    assert svc.tasks[tid]["status"] == "completed"
