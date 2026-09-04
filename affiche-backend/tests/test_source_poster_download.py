from contextlib import contextmanager
from unittest.mock import MagicMock

import affiche.app.mediaserver.service.source_poster_service as poster_module
from affiche.app.mediaserver.service.source_poster_service import SourcePosterService
from affiche.app.mediaserver.library.model import Library
from affiche.app.mediaserver.library.model.library_item import LibraryItem
from affiche.app.mediaserver.library.seasons.model.library_season import LibrarySeason

def _library(**kw):
    defaults = dict(id=1, media_server_id=1, external_id="L1", name="Lib",
                    type="movie", language="en", enabled=True)
    defaults.update(kw)
    return Library(**defaults)

def _service(monkeypatch, items, seasons_by_item=None, existing=()):
    seasons_by_item = seasons_by_item or {}
    svc = object.__new__(SourcePosterService)

    repo = MagicMock()
    repo.get_library.return_value = _library(type="show")
    repo.find_libraries.return_value = [_library(type="show")]
    repo.find_items.return_value = items

    season_service = MagicMock()
    season_service.get_item_seasons.side_effect = \
        lambda library_id, item_id, *a, **k: seasons_by_item.get(item_id, [])
    monkeypatch.setattr(poster_module, "LibrarySeasonService", lambda session: season_service)

    @contextmanager
    def _scope():
        yield repo, MagicMock()

    svc._session_scope = _scope

    file_store = MagicMock()
    existing = set(existing)

    def _exists(library, item_id, season_number=None, **k):
        key = (library, item_id) if season_number is None else (library, item_id, season_number)
        return key in existing

    file_store.exists.side_effect = _exists
    svc._file_store = file_store

    monkeypatch.setattr(poster_module, "fetch_as_jpeg", MagicMock(return_value=b"jpeg-bytes"))
    return svc, file_store

def _item(id, poster_url="http://plex/poster", processed=False, type="movie"):
    return LibraryItem(id=id, library_id=1, external_id=f"e{id}", title=f"T{id}",
                       type=type, processed=processed, poster_url=poster_url)

def _season(id, item_id, season_number, poster_url="http://plex/season", processed=False):
    return LibrarySeason(id=id, show_id=item_id, library_id=1, external_id=f"s{id}",
                         season_number=season_number, title=f"S{season_number}",
                         processed=processed, poster_url=poster_url)

def test_downloads_pending_item_with_poster_url(monkeypatch):
    em = MagicMock()
    monkeypatch.setattr(poster_module, "event_manager", em)
    svc, fs = _service(monkeypatch, [_item(1)])

    svc.download_source_posters(media_server_id=1, library_id=1)

    fs.save.assert_called_once_with(1, 1, b"jpeg-bytes")
    em.publish_item_processed.assert_called_once_with(1, 1, processed=False)

def test_skips_processed_item(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc, fs = _service(monkeypatch, [_item(1, processed=True)])

    svc.download_source_posters(media_server_id=1, library_id=1)

    fs.save.assert_not_called()

def test_skips_item_without_poster_url(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc, fs = _service(monkeypatch, [_item(1, poster_url=None)])

    svc.download_source_posters(media_server_id=1, library_id=1)

    fs.save.assert_not_called()

def test_skips_item_with_existing_file(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc, fs = _service(monkeypatch, [_item(1)], existing={(1, 1)})

    svc.download_source_posters(media_server_id=1, library_id=1)

    fs.save.assert_not_called()

def test_one_failing_job_does_not_abandon_the_rest(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    svc, fs = _service(monkeypatch, [_item(1), _item(2), _item(3)])
    download = svc._download_source_poster

    def flaky(kind, item, season):
        if item.id == 2:
            raise RuntimeError("the worker never saw this one")
        return download(kind, item, season)

    svc._download_source_poster = flaky

    svc.download_source_posters(media_server_id=1, library_id=1)

    assert {c.args[1] for c in fs.save.call_args_list} == {1, 3}

def test_downloads_pending_seasons(monkeypatch):
    monkeypatch.setattr(poster_module, "event_manager", MagicMock())
    show = _item(1, type="show")
    seasons = {1: [_season(10, 1, 1), _season(11, 1, 2, processed=True)]}
    svc, fs = _service(monkeypatch, [show], seasons_by_item=seasons)

    svc.download_source_posters(media_server_id=1, library_id=1)

    saved = {tuple(c.args) + tuple(sorted(c.kwargs.items())) for c in fs.save.call_args_list}
    assert (1, 1, b"jpeg-bytes") in saved
    assert (1, 1, b"jpeg-bytes", ("season_number", 1)) in saved
    assert not any(c.kwargs.get("season_number") == 2 for c in fs.save.call_args_list)
