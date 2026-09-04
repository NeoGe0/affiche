from contextlib import contextmanager
from unittest.mock import MagicMock

import affiche.app.mediaserver.service.poster_resetter as resetter_module
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
from affiche.app.mediaserver.service.media_server_connector_protocol import ResetResult
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.library.model import LibraryItem

def _svc():
    svc = object.__new__(LibraryPosterService)
    svc._file_store = MagicMock()
    svc._resetter = PosterResetter(file_store=svc._file_store,
                                   session_factory=MagicMock())
    return svc

def test_reset_poster_resets_a_failed_item(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _svc()
    repo, connector = MagicMock(), MagicMock()
    connector.reset_poster.return_value = ResetResult(True)
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie",
                       processed=False, error_message="No poster found from any provider")

    svc._resetter.reset_poster(repo, item, connector)

    connector.reset_poster.assert_called_once_with("x")
    assert item.error_message is None
    repo.create_or_update_item.assert_called_once()

def test_reset_poster_skips_an_untouched_item_by_default(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _svc()
    repo, connector = MagicMock(), MagicMock()
    connector.reset_poster.return_value = ResetResult(True)
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie", processed=False)

    svc._resetter.reset_poster(repo, item, connector)

    connector.reset_poster.assert_not_called()
    repo.create_or_update_item.assert_not_called()
    svc._file_store.delete.assert_not_called()

def test_reset_poster_resets_unprocessed_when_included(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _svc()
    repo, connector = MagicMock(), MagicMock()
    connector.reset_poster.return_value = ResetResult(True)
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie", processed=False)

    svc._resetter.reset_poster(repo, item, connector, include_unprocessed=True)

    connector.reset_poster.assert_called_once_with("x")
    repo.create_or_update_item.assert_called_once()
    svc._file_store.delete.assert_called_once()

def _library_reset_query(monkeypatch, include_unprocessed):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _svc()
    repo = MagicMock()
    repo.find_items.return_value = []

    @contextmanager
    def fake_scope(_session_factory=None):
        yield repo, MagicMock()

    monkeypatch.setattr(resetter_module, "library_session", fake_scope)
    svc._session_factory = MagicMock()
    svc._get_connector = MagicMock()

    svc._resetter.reset_library_posters(1, 10, MagicMock(),
                                        include_unprocessed=include_unprocessed)
    return repo.find_items.call_args.args[0]

def test_reset_library_selects_every_attempted_item_by_default(monkeypatch):
    search = _library_reset_query(monkeypatch, include_unprocessed=False)
    assert search.attempted is True
    assert search.processed is None

def test_reset_library_selects_all_when_including_unprocessed(monkeypatch):
    search = _library_reset_query(monkeypatch, include_unprocessed=True)
    assert search.attempted is None
    assert search.processed is None

def test_reset_library_does_not_exclude_locked_items(monkeypatch):
    search = _library_reset_query(monkeypatch, include_unprocessed=False)
    assert search.locked is None
