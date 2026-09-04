from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

import affiche.app.mediaserver.service.media_server_poster_service as poster_module
from affiche.app.mediaserver.library.model import Library
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.config.exceptions.exceptions import LibraryDisabledException, NotFoundError

def _library(enabled: bool) -> Library:
    return Library(id=10, media_server_id=1, external_id="L1", name="Movies",
                   type="movie", language="en", enabled=enabled)

def _service(monkeypatch, library: Library):
    svc = object.__new__(LibraryPosterService)
    svc._session_factory = MagicMock()

    repo = MagicMock()
    repo.get_library.return_value = library

    @contextmanager
    def fake_scope(_session_factory=None):
        yield repo, MagicMock()

    monkeypatch.setattr(poster_module, "library_session", fake_scope)
    return svc

def test_disabled_library_raises_the_domain_exception(monkeypatch):
    svc = _service(monkeypatch, _library(enabled=False))
    svc._process_library = MagicMock()

    with pytest.raises(LibraryDisabledException) as excinfo:
        svc.apply_posters_to_library(media_server_id=1, library_id=10)

    assert "10" in excinfo.value.message
    svc._process_library.assert_not_called()

def test_disabled_is_not_a_not_found(monkeypatch):
    svc = _service(monkeypatch, _library(enabled=False))
    svc._process_library = MagicMock()

    with pytest.raises(LibraryDisabledException) as excinfo:
        svc.apply_posters_to_library(media_server_id=1, library_id=10)

    assert not isinstance(excinfo.value, NotFoundError)

def test_the_app_layer_does_not_import_fastapi(monkeypatch):
    import inspect

    source = inspect.getsource(poster_module)
    assert "fastapi" not in source

def test_enabled_library_still_processes(monkeypatch):
    svc = _service(monkeypatch, _library(enabled=True))
    svc._process_library = MagicMock()

    svc.apply_posters_to_library(media_server_id=1, library_id=10)

    svc._process_library.assert_called_once()
