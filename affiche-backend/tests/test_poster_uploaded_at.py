from contextlib import contextmanager
from unittest.mock import MagicMock

import affiche.app.mediaserver.service.media_server_poster_service as poster_module
import affiche.app.mediaserver.service.poster_resetter as resetter_module
import affiche.app.mediaserver.service.poster_uploader as poster_uploader_module
from affiche.app.mediaserver.service.media_server_connector_protocol import ResetResult
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
from affiche.app.mediaserver.service.poster_uploader import PosterUploader
from affiche.app.mediaserver.library.model import LibraryItem

def _fake_session_scope(repo):
    @contextmanager
    def _scope(_session_factory=None):
        yield repo, MagicMock()
    return _scope

def _service_with_mocks():
    svc = object.__new__(LibraryPosterService)
    svc._decorator = MagicMock()
    svc._decorator.decorate_poster.return_value = b"poster-bytes"
    svc._file_store = MagicMock()
    svc._file_store.save.return_value = "/tmp/poster.jpg"
    svc._uploader = PosterUploader(file_store=svc._file_store, session_factory=MagicMock())
    svc._resetter = PosterResetter(file_store=svc._file_store, session_factory=MagicMock())
    return svc

def test_process_item_poster_stamps_poster_uploaded_at_when_uploaded(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    connector.upload_poster.return_value = True
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie")

    result = svc._process_item_poster(repo, MagicMock(), item, "http://poster", connector, upload=True)

    assert result is True
    connector.upload_poster.assert_called_once()
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.processed is True
    assert saved.poster_uploaded_at is not None

def test_process_item_poster_leaves_uploaded_at_null_when_not_uploaded(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie")

    result = svc._process_item_poster(repo, MagicMock(), item, "http://poster", connector, upload=False)

    assert result is True
    connector.upload_poster.assert_not_called()
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.processed is True
    assert saved.poster_uploaded_at is None

def test_upload_existing_item_poster_stamps_on_success(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    svc._file_store.exists.return_value = True
    svc._file_store.path.return_value = "/tmp/poster.jpg"
    repo = MagicMock()
    monkeypatch.setattr(poster_uploader_module, "library_session", _fake_session_scope(repo))
    connector = MagicMock()
    connector.upload_poster.return_value = True
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie", processed=True)

    assert svc._uploader.upload_existing_item_poster(item, connector) is True
    connector.upload_poster.assert_called_once_with("x", "/tmp/poster.jpg")
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_uploaded_at is not None

def test_upload_existing_item_poster_skips_when_no_stored_poster(monkeypatch):
    svc = _service_with_mocks()
    svc._file_store.exists.return_value = False
    connector = MagicMock()
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie", processed=True)

    assert svc._uploader.upload_existing_item_poster(item, connector) is False
    connector.upload_poster.assert_not_called()

def test_upload_existing_item_poster_no_stamp_when_upload_fails(monkeypatch):
    svc = _service_with_mocks()
    svc._file_store.exists.return_value = True
    svc._file_store.path.return_value = "/tmp/poster.jpg"
    connector = MagicMock()
    connector.upload_poster.return_value = False
    item = LibraryItem(id=1, library_id=1, external_id="x", title="T", type="movie", processed=True)

    assert svc._uploader.upload_existing_item_poster(item, connector) is False
    assert item.poster_uploaded_at is None

def test_reset_poster_clears_poster_uploaded_at(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    connector.reset_poster.return_value = ResetResult(True)
    from datetime import datetime, timezone
    item = LibraryItem(
        id=1, library_id=1, external_id="x", title="T", type="movie",
        processed=True, poster_uploaded_at=datetime.now(timezone.utc),
    )

    svc._resetter.reset_poster(repo, item, connector)

    repo.create_or_update_item.assert_called_once()
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.processed is False
    assert saved.poster_uploaded_at is None
