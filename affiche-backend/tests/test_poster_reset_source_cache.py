from unittest.mock import MagicMock

import pytest

import affiche.app.mediaserver.service.poster_resetter as resetter_module
from affiche.app.mediaserver.service.poster_resetter import PosterResetter
from affiche.app.mediaserver.service.media_server_connector_protocol import ResetResult
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.library.model import LibraryItem
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason

@pytest.fixture(autouse=True)
def _quiet_events(monkeypatch):
    monkeypatch.setattr(resetter_module, "event_manager", MagicMock())

@pytest.fixture
def fetch(monkeypatch):
    stub = MagicMock(return_value=b"jpeg-bytes")
    monkeypatch.setattr(resetter_module, "fetch_as_jpeg", stub)
    return stub

def _svc():
    svc = object.__new__(LibraryPosterService)
    svc._file_store = MagicMock()
    svc._resetter = PosterResetter(file_store=svc._file_store,
                                   session_factory=MagicMock())
    return svc

def _item(**kw):
    defaults = dict(id=1, library_id=7, external_id="x", title="T", type="movie",
                    processed=True, poster_url="http://plex/old")
    defaults.update(kw)
    return LibraryItem(**defaults)

def _connector(poster_url="http://plex/new", read_back=None):
    connector = MagicMock()
    connector.reset_poster.return_value = ResetResult(True, poster_url)
    connector.get_poster_url.return_value = read_back
    return connector

def test_reset_caches_the_poster_the_reset_selected(fetch):
    svc, repo, connector = _svc(), MagicMock(), _connector()
    item = _item()

    svc._resetter.reset_poster(repo, item, connector)

    connector.get_poster_url.assert_not_called()
    fetch.assert_called_once_with("http://plex/new")
    svc._file_store.save.assert_called_once_with(7, 1, b"jpeg-bytes", season_number=None)
    assert repo.create_or_update_item.call_args.args[0].poster_url == "http://plex/new"

def test_reset_reads_the_url_back_when_the_connector_cannot_name_it(fetch):
    svc, repo = _svc(), MagicMock()
    connector = _connector(poster_url=None, read_back="http://plex/read-back")

    svc._resetter.reset_poster(repo, _item(), connector)

    connector.get_poster_url.assert_called_once_with("x")
    fetch.assert_called_once_with("http://plex/read-back")

def test_reset_caches_after_deleting_the_generated_poster(fetch):
    svc, repo, connector = _svc(), MagicMock(), _connector()
    calls = []
    svc._file_store.delete.side_effect = lambda *a, **k: calls.append("delete")
    svc._file_store.save.side_effect = lambda *a, **k: calls.append("save")

    svc._resetter.reset_poster(repo, item := _item(), connector)

    assert calls == ["delete", "save"]
    assert item.processed is False

def test_reset_survives_a_failed_download(fetch):
    svc, repo, connector = _svc(), MagicMock(), _connector()
    fetch.side_effect = RuntimeError("boom")
    item = _item()

    svc._resetter.reset_poster(repo, item, connector)

    saved = repo.create_or_update_item.call_args.args[0]
    assert saved.processed is False
    assert saved.poster_hash is None
    assert saved.poster_url == "http://plex/old"

def test_reset_skips_caching_when_the_server_has_no_poster(fetch):
    svc, repo = _svc(), MagicMock()
    connector = _connector(poster_url=None, read_back=None)

    svc._resetter.reset_poster(repo, _item(), connector)

    fetch.assert_not_called()
    svc._file_store.save.assert_not_called()
    repo.create_or_update_item.assert_called_once()

def test_reset_caches_season_posters(fetch):
    svc, connector = _svc(), _connector()
    item = _item(type="show")
    season = LibrarySeason(id=3, library_id=7, show_id=1, external_id="s1",
                           season_number=2, title="Season 2", poster_url="http://plex/old-s2")
    season_service = MagicMock()
    season_service.get_item_seasons.return_value = [season]

    svc._resetter.reset_season_posters(season_service, item, connector)

    svc._file_store.save.assert_called_once_with(7, 1, b"jpeg-bytes", season_number=2)
    assert season.poster_url == "http://plex/new"
    season_service.create_or_update.assert_called_once_with([season])
