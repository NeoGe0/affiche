from unittest.mock import MagicMock

import affiche.app.asynch.library_tasks as tasks

def _fake_container(monkeypatch):
    service = MagicMock()
    container = MagicMock()
    container.poster_sync_service.return_value = service
    monkeypatch.setattr(tasks, "container", container)
    return service

def test_global_generation_syncs_before_generating(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks, "sync_libraries_task",
                        lambda ms, cancel_check=None: calls.append("sync"))
    service = _fake_container(monkeypatch)
    service.apply_posters_to_all_libraries.side_effect = lambda **k: calls.append("generate")

    tasks.sync_posters_task(5)

    assert calls == ["sync", "generate"]

def test_per_library_generation_syncs_before_generating(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks, "sync_library_task",
                        lambda ms, lib_id, cancel_check=None, incremental=False:
                        calls.append("sync"))
    service = _fake_container(monkeypatch)
    service.apply_posters_to_library.side_effect = lambda *a, **k: calls.append("generate")

    tasks.sync_library_posters_task(5, 10)

    assert calls == ["sync", "generate"]

def test_generation_skipped_when_cancelled_after_sync(monkeypatch):
    monkeypatch.setattr(tasks, "sync_libraries_task", lambda ms, cancel_check=None: None)
    service = _fake_container(monkeypatch)

    tasks.sync_posters_task(5, cancel_check=lambda: True)

    service.apply_posters_to_all_libraries.assert_not_called()

def test_the_router_submits_the_shared_task_bodies(monkeypatch):
    import affiche.api.routers.library as router

    assert router.library_tasks is tasks

def test_auto_pickup_runs_the_same_bodies_as_a_manual_run():
    import affiche.app.asynch.auto_pickup as auto_pickup

    assert auto_pickup.sync_library_task is tasks.sync_library_task
    assert auto_pickup.sync_library_posters_task is tasks.sync_library_posters_task
