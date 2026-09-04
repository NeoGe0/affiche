import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import affiche.main as main_module
from affiche.app.asynch.async_task_service import AsyncTaskService
from affiche.app.task_history import TaskRunSearch, MAX_RUNS, TaskHistoryService, parse_task_scope
from affiche.app.task_history.task_history_recorder import make_task_recorder
from affiche.config import Base
from affiche.config.database import SessionLocal

@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()

@pytest.fixture
def db(session_factory):
    session = session_factory()
    yield session
    session.close()

@pytest.fixture
def history(db):
    return TaskHistoryService(db)

def _task(**overrides) -> dict:
    task = {
        "status": "running",
        "task_name": "poster_generation",
        "blocking": True,
        "resource": "ms:1:lib:7",
        "created_at": "2026-08-27T10:00:00",
        "started_at": "2026-08-27T10:00:01",
    }
    task.update(overrides)
    return task

class TestParseTaskScope:

    def test_a_library_scoped_key_yields_both_ids(self):
        assert parse_task_scope("ms:3:lib:12") == (3, 12)

    def test_a_server_wide_key_yields_no_library(self):
        assert parse_task_scope("ms:3:*") == (3, None)

    def test_an_unscoped_task_yields_nothing(self):
        assert parse_task_scope(None) == (None, None)
        assert parse_task_scope("") == (None, None)

    def test_an_unrecognised_key_yields_nothing_rather_than_a_guess(self):
        assert parse_task_scope("something:else") == (None, None)
        assert parse_task_scope("ms:not-a-number:lib:4") == (None, None)
        assert parse_task_scope("ms:3:lib:not-a-number") == (3, None)

class TestRecording:

    def test_a_run_is_recorded_with_the_ids_parsed_out_of_its_resource(self, history):
        history.record("task-1", _task())

        run = history.find_recent(TaskRunSearch())[0]
        assert (run.task_id, run.task_name, run.status) == ("task-1", "poster_generation", "running")
        assert (run.media_server_id, run.library_id) == (1, 7)
        assert run.blocking is True

    def test_the_transitions_of_one_run_update_one_row(self, history):
        history.record("task-1", _task(status="pending"))
        history.record("task-1", _task(status="running"))
        history.record("task-1", _task(status="completed",
                                       completed_at="2026-08-27T10:05:00"))

        runs = history.find_recent(TaskRunSearch())
        assert len(runs) == 1
        assert runs[0].status == "completed"
        assert runs[0].ended_at.isoformat() == "2026-08-27T10:05:00"

    def test_a_failure_keeps_its_error(self, history):
        history.record("task-1", _task(status="failed", failed_at="2026-08-27T10:02:00",
                                       error="Connection refused",
                                       message="Task failed: Connection refused"))

        run = history.find_recent(TaskRunSearch())[0]
        assert (run.status, run.error) == ("failed", "Connection refused")
        assert run.ended_at is not None

    def test_a_cancellation_ends_the_run_too(self, history):
        history.record("task-1", _task(status="cancelled",
                                       cancelled_at="2026-08-27T10:03:00"))

        run = history.find_recent(TaskRunSearch())[0]
        assert (run.status, run.ended_at.isoformat()) == ("cancelled", "2026-08-27T10:03:00")

    def test_the_last_reported_progress_is_kept(self, history):
        history.record("task-1", _task(progress={"current": 40, "total": 100, "message": "…"}))

        run = history.find_recent(TaskRunSearch())[0]
        assert (run.items_done, run.items_total) == (40, 100)

    def test_a_terminal_write_does_not_blank_the_progress_it_carries_no_copy_of(self, history):
        history.record("task-1", _task(progress={"current": 100, "total": 100}))
        history.record("task-1", _task(status="completed", completed_at="2026-08-27T10:05:00"))

        run = history.find_recent(TaskRunSearch())[0]
        assert (run.items_done, run.items_total) == (100, 100)
        assert run.status == "completed"

    def test_a_run_that_never_reported_progress_has_none_rather_than_zero(self, history):
        history.record("task-1", _task())

        run = history.find_recent(TaskRunSearch())[0]
        assert (run.items_done, run.items_total) == (None, None)

    def test_recording_never_raises_on_a_malformed_task(self, history):
        assert history.record("task-1", {"status": "running", "created_at": "not-a-date"}) is not None
        assert history.record("task-2", {}) is not None

    def test_the_newest_run_comes_first(self, history):
        history.record("old", _task(created_at="2026-08-27T09:00:00"))
        history.record("new", _task(created_at="2026-08-27T11:00:00"))

        assert [run.task_id for run in history.find_recent(TaskRunSearch())] == ["new", "old"]

    def test_runs_can_be_read_for_one_library(self, history):
        history.record("here", _task(resource="ms:1:lib:7"))
        history.record("elsewhere", _task(resource="ms:1:lib:9"))
        history.record("server-wide", _task(resource="ms:1:*"))

        assert [run.task_id for run in history.find_recent(TaskRunSearch(library_id=7))] == ["here"]

    def test_history_is_capped(self, history):
        for index in range(MAX_RUNS + 10):
            history.record(f"task-{index:04d}",
                           _task(status="completed", created_at=f"2026-08-27T10:00:{index % 60:02d}",
                                 completed_at="2026-08-27T10:30:00"))

        assert len(history.find_recent(TaskRunSearch(page_size=MAX_RUNS + 100))) == MAX_RUNS

    def test_the_cap_drops_the_oldest_not_the_newest(self, history):
        for index in range(MAX_RUNS):
            history.record(f"old-{index}", _task(status="completed",
                                                 created_at="2026-08-27T09:00:00",
                                                 completed_at="2026-08-27T09:01:00"))
        history.record("newest", _task(status="completed", created_at="2026-08-27T23:00:00",
                                       completed_at="2026-08-27T23:01:00"))

        assert history.find_recent(TaskRunSearch())[0].task_id == "newest"

    def test_an_active_run_does_not_trigger_the_prune(self, history):
        for index in range(MAX_RUNS + 5):
            history.record(f"task-{index}", _task(status="running"))

        assert len(history.find_recent(TaskRunSearch(page_size=MAX_RUNS + 100))) == MAX_RUNS + 5

class TestRunnerIntegration:

    def test_every_status_transition_of_a_real_task_is_recorded(self, session_factory, db):
        service = AsyncTaskService(history=make_task_recorder(session_factory))

        task_id, _ = service.submit_detached_task(lambda cancel_check=None: None, "sync_libraries")
        service._executor.shutdown(wait=True)

        run = TaskHistoryService(db).find_recent(TaskRunSearch())[0]
        assert run.task_id == task_id
        assert run.status == "completed"
        assert run.started_at is not None and run.ended_at is not None

    def test_a_failing_task_lands_in_history_with_its_error(self, session_factory, db):
        def explode(cancel_check=None):
            raise RuntimeError("the media server said no")

        service = AsyncTaskService(history=make_task_recorder(session_factory))
        service.submit_detached_task(explode, "poster_generation")
        service._executor.shutdown(wait=True)

        run = TaskHistoryService(db).find_recent(TaskRunSearch())[0]
        assert run.status == "failed"
        assert run.error == "the media server said no"

    def test_a_sink_that_throws_does_not_fail_the_task(self, db):
        def broken_sink(task_id, task):
            raise RuntimeError("disk is full")

        service = AsyncTaskService(history=broken_sink)
        task_id, _ = service.submit_detached_task(lambda cancel_check=None: None, "sync_libraries")
        service._executor.shutdown(wait=True)

        assert service.get_task_status(task_id)["status"] == "completed"

    def test_the_runner_works_with_no_history_at_all(self, db):
        service = AsyncTaskService()
        task_id, _ = service.submit_detached_task(lambda cancel_check=None: None, "sync_libraries")
        service._executor.shutdown(wait=True)

        assert service.get_task_status(task_id)["status"] == "completed"

def test_the_dashboard_serves_recent_activity_from_the_table(authenticated_app):
    with TestClient(authenticated_app) as client:
        session = SessionLocal()
        try:
            TaskHistoryService(session).record("dash-task", _task(
                status="failed", failed_at="2026-08-27T10:02:00", error="boom",
                message="Task failed: boom"))
        finally:
            session.close()

        resp = client.get("/affiche/dashboard")

    assert resp.status_code == 200
    task = next(t for t in resp.json()["recent_tasks"] if t["task_id"] == "dash-task")
    assert (task["status"], task["error"]) == ("failed", "boom")
    assert task["created_at"] == "2026-08-27T10:00:00"
    assert task["completed_at"] == "2026-08-27T10:02:00"

def test_recent_activity_survives_a_restart_of_the_task_runner(authenticated_app):
    with TestClient(authenticated_app) as client:
        session = SessionLocal()
        try:
            TaskHistoryService(session).record("survivor", _task(
                status="completed", completed_at="2026-08-27T10:05:00"))
        finally:
            session.close()

        from affiche.config.dependencies import container
        container.async_task_service.tasks.clear()

        resp = client.get("/affiche/dashboard")

    assert any(t["task_id"] == "survivor" for t in resp.json()["recent_tasks"])

def test_the_dashboard_is_still_session_gated():
    with TestClient(main_module.app) as client:
        assert client.get("/affiche/dashboard").status_code == 401
