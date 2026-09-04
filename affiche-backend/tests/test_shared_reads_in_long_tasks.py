from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import affiche.api.routers.library  # noqa: F401  (warm the api package; avoids an import cycle)
import affiche.app.mediaserver.service.media_server_poster_service as poster_module
from affiche.app.image.model.overlay_options import OverlayOptions
from affiche.app.mediaserver.library.model import Library
from affiche.app.mediaserver.service.jellyfin_sync_service import JellyfinSynchronisationService
from affiche.app.mediaserver.service.media_server_poster_service import LibraryPosterService
from affiche.app.mediaserver.service.plex_sync_service import PlexSynchronisationService
from affiche.app.mediaserver.model.media_server import MediaServer, MediaServerType
from affiche.external.jellyfin.service.jellyfin_service import JellyfinService
from affiche.external.plex.service.plex_service import PlexService

def _items(count: int) -> list:
    return [SimpleNamespace(id=i, title=f"item {i}", library_id=10) for i in range(count)]

def _generation_service(monkeypatch, item_count: int) -> LibraryPosterService:
    svc = object.__new__(LibraryPosterService)
    svc._session_factory = MagicMock()
    svc._connector_factory = MagicMock()

    repo = MagicMock()
    repo.find_items.return_value = _items(item_count)

    @contextmanager
    def fake_scope(_session_factory=None):
        yield repo, MagicMock()

    monkeypatch.setattr(poster_module, "library_session", fake_scope)

    svc._get_server_poster_settings = MagicMock()
    svc._get_upload_enabled = MagicMock(return_value=False)
    svc._get_library_style = MagicMock(return_value=poster_module.GLOBAL_STYLE)
    svc._process_item = MagicMock(return_value=True)
    return svc

def _library() -> Library:
    return Library(id=10, media_server_id=1, external_id="L1", name="Movies",
                   type="movie", language="en", enabled=True)

def test_provider_order_is_read_once_per_library_not_once_per_item(monkeypatch):
    svc = _generation_service(monkeypatch, item_count=25)
    svc._get_provider_order = MagicMock(return_value=["tmdb"])

    svc._process_library(media_server_id=1, library=_library())

    assert svc._get_provider_order.call_count == 1, (
        f"read {svc._get_provider_order.call_count}x for 25 items — back to a SELECT per item")

def test_the_hoisted_provider_order_reaches_every_item(monkeypatch):
    svc = _generation_service(monkeypatch, item_count=5)
    svc._get_provider_order = MagicMock(return_value=["tmdb", "fanart"])

    svc._process_library(media_server_id=1, library=_library())

    assert svc._process_item.call_count == 5
    for call in svc._process_item.call_args_list:
        assert ["tmdb", "fanart"] in call.args

def test_library_style_is_read_once_and_reaches_every_item(monkeypatch):
    style = poster_module.LibraryPosterStyle(overlay_options=OverlayOptions(border_px=7),
                                             text_options=None)
    svc = _generation_service(monkeypatch, item_count=25)
    svc._get_provider_order = MagicMock(return_value=["tmdb"])
    svc._get_library_style = MagicMock(return_value=style)

    svc._process_library(media_server_id=1, library=_library())

    assert svc._get_library_style.call_count == 1
    assert svc._process_item.call_count == 25
    for call in svc._process_item.call_args_list:
        assert style in call.args

def test_server_poster_settings_stay_hoisted_too(monkeypatch):
    svc = _generation_service(monkeypatch, item_count=25)
    svc._get_provider_order = MagicMock(return_value=["tmdb"])

    svc._process_library(media_server_id=1, library=_library())

    assert svc._get_server_poster_settings.call_count == 1

def _media_server(server_type: MediaServerType) -> MediaServer:
    return MediaServer(id=7, name="S", type=server_type, url="http://x", token="t")

def _sync_service(cls, connector):
    factory = MagicMock()
    factory.get.return_value = connector
    svc = cls(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),
              factory)
    svc._sync_library = lambda *a, **k: None
    svc._sync_single_library = lambda *a, **k: None
    return svc, factory

def test_plex_sync_takes_its_connector_from_the_shared_factory():
    connector = MagicMock(spec=PlexService)
    svc, factory = _sync_service(PlexSynchronisationService, connector)
    svc.library_service.find_libraries.return_value = []

    svc.sync_plex_libraries(_media_server(MediaServerType.PLEX))

    factory.get.assert_called_once_with(7)

def test_jellyfin_sync_takes_its_connector_from_the_shared_factory():
    connector = MagicMock(spec=JellyfinService)
    svc, factory = _sync_service(JellyfinSynchronisationService, connector)
    svc.library_service.find_libraries.return_value = []

    svc.sync_jellyfin_libraries(_media_server(MediaServerType.JELLYFIN))

    factory.get.assert_called_once_with(7)

def test_sync_never_constructs_a_connector_directly(monkeypatch):
    constructed = []
    monkeypatch.setattr(PlexService, "__init__",
                        lambda self, base_url, token: constructed.append(base_url))

    connector = MagicMock(spec=PlexService)
    svc, factory = _sync_service(PlexSynchronisationService, connector)
    svc.library_service.find_libraries.return_value = []
    server = _media_server(MediaServerType.PLEX)

    svc.sync_plex_libraries(server)
    svc.sync_plex_libraries(server)

    assert constructed == [], f"built {len(constructed)} PlexService(s) instead of using the factory"
    assert [c.args for c in factory.get.call_args_list] == [(7,), (7,)]
