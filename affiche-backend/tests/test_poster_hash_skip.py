from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import affiche.app.mediaserver.service.media_server_poster_service as poster_module
import affiche.app.mediaserver.service.poster_resetter as resetter_module
import affiche.app.mediaserver.service.poster_uploader as poster_uploader_module
from affiche.app.filestore.filestore import poster_digest
from affiche.app.mediaserver.service.media_server_connector_protocol import ResetResult
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
from affiche.app.mediaserver.service.poster_uploader import PosterUploader
from affiche.app.mediaserver.library.model import LibraryItem, LibrarySeason

POSTER_BYTES = b"poster-bytes"
STYLE_HASH = "style-fingerprint"
POSTER_HASH = poster_digest(POSTER_BYTES)

def _fake_session_scope(repo):
    @contextmanager
    def _scope(_session_factory=None):
        yield repo, MagicMock()
    return _scope

def _service_with_mocks():
    svc = object.__new__(LibraryPosterService)
    svc._decorator = MagicMock()
    svc._decorator.decorate_poster.return_value = POSTER_BYTES
    svc._decorator.style_fingerprint.return_value = STYLE_HASH
    svc._file_store = MagicMock()
    svc._file_store.save.return_value = "/tmp/poster.jpg"
    svc._file_store.path.return_value = "/tmp/poster.jpg"
    svc._file_store.exists.return_value = True
    svc._file_store.digest.return_value = POSTER_HASH
    svc._uploader = PosterUploader(file_store=svc._file_store, session_factory=MagicMock())
    svc._resetter = PosterResetter(file_store=svc._file_store, session_factory=MagicMock())
    return svc

def _item(**overrides) -> LibraryItem:
    fields = dict(id=1, library_id=1, external_id="x", title="T", type="movie", processed=True)
    fields.update(overrides)
    return LibraryItem(**fields)

def _season(**overrides) -> LibrarySeason:
    fields = dict(id=7, show_id=1, library_id=1, external_id="s1", season_number=1, title="Season 1")
    fields.update(overrides)
    return LibrarySeason(**fields)

def test_process_item_poster_skips_upload_when_hash_matches(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    uploaded_at = datetime.now(timezone.utc) - timedelta(days=1)
    item = _item(poster_hash=POSTER_HASH, poster_uploaded_at=uploaded_at)

    assert svc._process_item_poster(repo, MagicMock(), item, "http://poster", connector, upload=True) is True

    connector.upload_poster.assert_not_called()
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_hash == POSTER_HASH
    assert saved.poster_uploaded_at == uploaded_at

def test_process_item_poster_uploads_and_stores_hash_when_content_differs(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    connector.upload_poster.return_value = True
    item = _item(poster_hash="stale-hash")

    assert svc._process_item_poster(repo, MagicMock(), item, "http://poster", connector, upload=True) is True

    connector.upload_poster.assert_called_once()
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_hash == POSTER_HASH
    assert saved.poster_uploaded_at is not None

def test_process_item_poster_keeps_hash_when_generating_without_upload(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    item = _item(poster_hash=POSTER_HASH, poster_uploaded_at=datetime.now(timezone.utc))

    assert svc._process_item_poster(repo, MagicMock(), item, "http://poster", connector, upload=False) is True

    connector.upload_poster.assert_not_called()
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_hash == POSTER_HASH
    assert saved.poster_uploaded_at is None

def test_process_item_poster_keeps_hash_when_upload_fails(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    connector.upload_poster.return_value = False
    item = _item(poster_hash="stale-hash")

    assert svc._process_item_poster(repo, MagicMock(), item, "http://poster", connector, upload=True) is True

    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_hash == "stale-hash"
    assert saved.poster_uploaded_at is None

def test_upload_existing_item_poster_skips_when_hash_matches(monkeypatch):
    svc = _service_with_mocks()
    repo = MagicMock()
    monkeypatch.setattr(poster_uploader_module, "library_session", _fake_session_scope(repo))
    connector = MagicMock()
    item = _item(poster_hash=POSTER_HASH)

    assert svc._uploader.upload_existing_item_poster(item, connector) is True

    connector.upload_poster.assert_not_called()
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_uploaded_at is not None

def test_upload_existing_item_poster_uploads_when_hash_differs(monkeypatch):
    svc = _service_with_mocks()
    repo = MagicMock()
    monkeypatch.setattr(poster_uploader_module, "library_session", _fake_session_scope(repo))
    connector = MagicMock()
    connector.upload_poster.return_value = True
    item = _item(poster_hash="stale-hash")

    assert svc._uploader.upload_existing_item_poster(item, connector) is True

    connector.upload_poster.assert_called_once_with("x", "/tmp/poster.jpg")
    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_hash == POSTER_HASH

def test_reset_poster_clears_poster_hash(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    repo = MagicMock()
    connector = MagicMock()
    connector.reset_poster.return_value = ResetResult(True)
    item = _item(poster_hash=POSTER_HASH, poster_uploaded_at=datetime.now(timezone.utc))

    svc._resetter.reset_poster(repo, item, connector)

    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.poster_hash is None

def _season_updates(season_service):
    return [(call.args[0], call.args[1].changes())
            for call in season_service.update_seasons.call_args_list]

def test_process_season_poster_skips_upload_when_hash_matches(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    season_service = MagicMock()
    connector = MagicMock()
    season = _season(poster_hash=POSTER_HASH)

    assert svc._process_season_poster(season_service, MagicMock(), season, _item(type="show"), "http://poster",
                                      connector, upload=True) is True

    connector.upload_poster.assert_not_called()
    (seasons, changes), = _season_updates(season_service)
    assert seasons == [season]
    assert changes["processed"] is True
    assert "poster_hash" not in changes

def test_process_season_poster_uploads_and_stores_hash_when_content_differs(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    season_service = MagicMock()
    connector = MagicMock()
    connector.upload_poster.return_value = True
    season = _season()

    assert svc._process_season_poster(season_service, MagicMock(), season, _item(type="show"), "http://poster",
                                      connector, upload=True) is True

    connector.upload_poster.assert_called_once()
    assert ([season], {"poster_hash": POSTER_HASH}) in _season_updates(season_service)

def test_upload_existing_season_posters_skips_unchanged_seasons():
    svc = _service_with_mocks()
    connector = MagicMock()
    connector.upload_poster.return_value = True
    unchanged = _season(id=7, season_number=1, external_id="s1", poster_hash=POSTER_HASH)
    changed = _season(id=8, season_number=2, external_id="s2", poster_hash="stale-hash")
    season_service = MagicMock()
    season_service.get_item_seasons.return_value = [unchanged, changed]

    svc._uploader.upload_existing_season_posters(season_service, _item(type="show"), connector)

    connector.upload_poster.assert_called_once()
    assert connector.upload_poster.call_args.args[0] == "s2"
    assert _season_updates(season_service) == [([changed], {"poster_hash": POSTER_HASH})]

def test_reset_season_posters_clears_poster_hash(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    connector = MagicMock()
    connector.reset_poster.return_value = ResetResult(True)
    seasons = [_season(poster_hash=POSTER_HASH)]
    season_service = MagicMock()
    season_service.get_item_seasons.return_value = seasons

    svc._resetter.reset_season_posters(season_service, _item(type="show"), connector)

    (updated, changes), = _season_updates(season_service)
    assert updated == seasons
    assert changes["poster_hash"] is None

def test_reset_season_posters_leaves_a_failed_season_untouched(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())
    svc = _service_with_mocks()
    connector = MagicMock()
    reset_ok = _season(id=7, season_number=1, external_id="s1", poster_hash=POSTER_HASH)
    failed = _season(id=8, season_number=2, external_id="s2", poster_hash=POSTER_HASH)
    connector.reset_poster.side_effect = lambda external_id: ResetResult(external_id == "s1")
    season_service = MagicMock()
    season_service.get_item_seasons.return_value = [reset_ok, failed]

    svc._resetter.reset_season_posters(season_service, _item(type="show"), connector)

    (updated, changes), = _season_updates(season_service)
    assert updated == [reset_ok]
    assert changes == {"processed": False, "poster_hash": None,
                       "poster_provider": None, "style_hash": None}
    season_service.create_or_update.assert_called_once_with([reset_ok])
    assert svc._file_store.delete.call_count == 1
    assert svc._file_store.delete.call_args.kwargs["season_number"] == 1
