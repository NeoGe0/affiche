import itertools
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

import affiche.app.mediaserver.service.poster_resetter as resetter_module
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
import affiche.app.mediaserver.service.poster_workers as poster_workers
from affiche.app.mediaserver.service.media_server_connector_protocol import ResetResult
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.library.model import LibraryItem

def _items(n):
    return [LibraryItem(id=i, library_id=10, external_id=f"x{i}", title=f"T{i}",
                        type="movie", processed=True) for i in range(1, n + 1)]

def _run_reset(monkeypatch, items, workers=None, fail_scope_call=None):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    monkeypatch.setattr(resetter_module, "fetch_as_jpeg", MagicMock(return_value=b"jpeg"))
    if workers is not None:
        monkeypatch.setattr(resetter_module, "RESET_MAX_WORKERS", workers)
    progress = MagicMock()
    monkeypatch.setattr(resetter_module, "report_task_progress", progress)

    svc = object.__new__(LibraryPosterService)
    svc._file_store = MagicMock()
    svc._resetter = PosterResetter(file_store=svc._file_store,
                                   session_factory=MagicMock())

    library = MagicMock()
    library.name = "Movies"
    repo = MagicMock()
    repo.find_items.return_value = items
    repo.get_library.return_value = library

    calls = itertools.count(1)

    @contextmanager
    def fake_scope(_session_factory=None):
        if next(calls) == fail_scope_call:
            raise RuntimeError("could not acquire a session")
        yield repo, MagicMock()

    monkeypatch.setattr(resetter_module, "library_session", fake_scope)
    svc._session_factory = MagicMock()
    connector = MagicMock()
    connector.reset_poster.return_value = ResetResult(True, "http://plex/new")
    svc._get_connector = MagicMock(return_value=connector)

    svc._resetter.reset_library_posters(1, 10, connector)
    return progress

def test_reset_reports_progress_for_every_item(monkeypatch):
    progress = _run_reset(monkeypatch, _items(5))

    assert progress.call_args_list[0].args[:2] == (0, 5)
    assert [c.args[0] for c in progress.call_args_list] == [0, 1, 2, 3, 4, 5]
    assert {c.args[1] for c in progress.call_args_list} == {5}

def test_reset_progress_is_labelled_with_the_library(monkeypatch):
    progress = _run_reset(monkeypatch, _items(1))

    assert progress.call_args.args[2] == "Resetting posters — Movies"

def test_reset_survives_an_item_that_cannot_open_a_session(monkeypatch):
    progress = _run_reset(monkeypatch, _items(5), workers=1, fail_scope_call=3)

    assert [c.args[0] for c in progress.call_args_list] == [0, 1, 2, 3, 4, 5]

def test_reset_honours_the_worker_override(monkeypatch):
    progress = _run_reset(monkeypatch, _items(12), workers=8)

    assert progress.call_args.args[0] == 12

@pytest.mark.parametrize("raw, expected", [
    (None, 4),
    ("", 4),
    ("12", 12),
    ("1", 1),
    ("nope", 4),
    ("0", 4),
    ("-3", 4),
])
def test_reset_max_workers_env_override(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("RESET_MAX_WORKERS", raising=False)
    else:
        monkeypatch.setenv("RESET_MAX_WORKERS", raw)

    assert poster_workers._env_worker_count("RESET_MAX_WORKERS", 4) == expected

def test_reset_max_workers_defaults_to_the_generation_pool():
    assert poster_workers.RESET_MAX_WORKERS == poster_workers.MAX_WORKERS
