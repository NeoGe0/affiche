from types import SimpleNamespace
from unittest.mock import MagicMock

from affiche.app.mediaserver.service.jellyfin_sync_service import JellyfinSynchronisationService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService

def _connector_factory() -> MagicMock:
    factory = MagicMock()
    factory.get.return_value = MagicMock(spec=JellyfinService)
    return factory

def _service(library_service) -> JellyfinSynchronisationService:
    return JellyfinSynchronisationService(
        library_service, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),
        _connector_factory(),
    )

def test_failing_library_does_not_abort_the_rest():
    library_service = MagicMock()
    library_service.find_libraries.return_value = [
        SimpleNamespace(name="A", enabled=True),
        SimpleNamespace(name="B", enabled=True),
    ]
    svc = _service(library_service)

    processed = []

    def fake_sync(_jellyfin_service, library, cancel_check=None):
        processed.append(library.name)
        if library.name == "A":
            raise RuntimeError("boom")

    svc._sync_single_library = fake_sync

    svc.sync_jellyfin_libraries(MediaServer(
        id=1, name="S", type=MediaServerType.JELLYFIN, url="http://x", token="t",
    ))

    assert processed == ["A", "B"]

def test_cancel_check_stops_single_library_sync_before_processing():
    library_service = MagicMock()
    svc = _service(library_service)

    jellyfin_service = MagicMock()
    jellyfin_service.get_library_items.return_value = [
        SimpleNamespace(id=1, title="t", type="movie", year=2000, added_at=None,
                        updated_at=None, imdb_id=None, tmdb_id=None, tvdb_id=None),
    ]
    library = SimpleNamespace(name="L", external_id="e1", id=1)

    svc._sync_single_library(jellyfin_service, library, cancel_check=lambda: True)

    library_service.create_or_update_items_batch.assert_not_called()

def _svc_with_items(items):
    library_service = MagicMock()
    library_service.reconcile_deletions.return_value = (0, 0)
    svc = _service(library_service)
    jellyfin_service = MagicMock()
    jellyfin_service.get_library_items.return_value = items
    jellyfin_service.get_show_seasons.return_value = []
    return svc, library_service, jellyfin_service

def _item(i):
    return SimpleNamespace(id=i, title=f"t{i}", type="movie", year=2000, added_at=None,
                           updated_at=None, imdb_id=None, tmdb_id=None, tvdb_id=None)

def test_reconciliation_runs_after_a_normal_sync():
    svc, library_service, jellyfin_service = _svc_with_items([_item(1), _item(2)])
    library = SimpleNamespace(name="L", external_id="e1", id=7)

    svc._sync_single_library(jellyfin_service, library)

    library_service.reconcile_deletions.assert_called_once()
    assert library_service.reconcile_deletions.call_args.args[0] == 7

def test_reconciliation_skipped_when_server_returns_no_items():
    svc, library_service, jellyfin_service = _svc_with_items([])
    library = SimpleNamespace(name="L", external_id="e1", id=7)

    svc._sync_single_library(jellyfin_service, library)

    library_service.reconcile_deletions.assert_not_called()

def test_reconciliation_skipped_when_cancelled_mid_run():
    svc, library_service, jellyfin_service = _svc_with_items([_item(1)])
    library = SimpleNamespace(name="L", external_id="e1", id=7)

    calls = {"n": 0}

    def cancel():
        calls["n"] += 1
        return calls["n"] > 1

    svc._sync_single_library(jellyfin_service, library, cancel_check=cancel)

    library_service.reconcile_deletions.assert_not_called()

def test_full_run_purges_expired_trash_once():
    library_service = MagicMock()
    library_service.find_libraries.return_value = [
        SimpleNamespace(name="A", enabled=True),
        SimpleNamespace(name="B", enabled=True),
    ]
    svc = _service(library_service)
    svc._sync_single_library = lambda *a, **k: None

    svc.sync_jellyfin_libraries(MediaServer(
        id=1, name="S", type=MediaServerType.JELLYFIN, url="http://x", token="t",
    ))

    library_service.purge_expired_trash.assert_called_once()
