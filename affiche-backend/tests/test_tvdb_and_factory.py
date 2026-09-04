from unittest.mock import MagicMock

import affiche.external.poster.provider.tvdb as tvdb_mod
import affiche.external.poster.poster_service_factory as factory_mod
from affiche.external.poster.provider.base_provider import BaseUrlMode, ExternalProvider
from affiche.external.poster.provider.tvdb import TVDBClient
from affiche.external.poster.poster_service_factory import PosterServiceFactory
from affiche.app.service_configuration.provider_service import EXTERNAL_PROVIDERS
from affiche.app.service_configuration.model.service_configuration import (
    ServiceConfiguration, ServiceType,
)

def test_construction_does_not_login(monkeypatch):
    spy = MagicMock()
    monkeypatch.setattr(tvdb_mod, "TVDB", spy)

    TVDBClient("api-key")

    spy.assert_not_called()

def test_client_built_lazily_and_cached(monkeypatch):
    spy = MagicMock()
    monkeypatch.setattr(tvdb_mod, "TVDB", spy)
    client = TVDBClient("api-key")

    client.get_show_poster(tvdb_id=1)
    client.get_show_poster(tvdb_id=2)

    assert spy.call_count == 1
    spy.assert_called_once_with("api-key")

def test_login_failure_is_fail_soft(monkeypatch):
    def boom(_api_key):
        raise RuntimeError("TVDB login failed / outage")

    monkeypatch.setattr(tvdb_mod, "TVDB", boom)
    client = TVDBClient("api-key")

    assert client.get_show_poster(tvdb_id=1) is None

def _provider_config(name: str, url: str = "https://api.example.com") -> ServiceConfiguration:
    return ServiceConfiguration(
        name=name, type=ServiceType.PROVIDER, token=f"{name}-token", url=url, enabled=True,
    )

class _OpenApiClient(ExternalProvider):

    requires_api_key = False
    base_url_mode = BaseUrlMode.NONE

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "open"

    def get_movie_poster(self, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_show_poster(self, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_season_poster(self, season_number, tmdb_id=None, tvdb_id=None, language=None):
        return None

    def get_all_posters(self, media_type, tmdb_id=None, tvdb_id=None, language=None):
        return []

    def get_all_season_posters(self, season_number, tmdb_id=None, tvdb_id=None, language=None):
        return []

    def test_connection(self, api_token) -> bool:
        return True

def _config_service_all_enabled() -> MagicMock:
    configs = {
        "tmdb": _provider_config("tmdb"),
        "tvdb": _provider_config("tvdb"),
        "fanart": _provider_config("fanart"),
        "mediux": _provider_config("mediux"),
        "tvmaze": _provider_config("tvmaze"),
        "shoko": _provider_config("shoko", url="http://localhost:8111"),
    }
    svc = MagicMock()
    svc.configs = configs
    svc.get_config.side_effect = configs.get
    return svc

ALL_PROVIDERS = {"tmdb", "tvdb", "fanart", "mediux", "tvmaze", "shoko"}

def test_all_providers_returned_when_healthy(monkeypatch):
    monkeypatch.setattr(tvdb_mod, "TVDB", MagicMock())
    factory = PosterServiceFactory(_config_service_all_enabled())

    services = factory.get_configured_services()

    assert {s.name for s in services} == ALL_PROVIDERS

def test_factory_skips_provider_that_fails_to_construct(monkeypatch):
    class raising_ctor(TVDBClient):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("cannot build TVDB client")

    monkeypatch.setitem(factory_mod.EXTERNAL_PROVIDERS, "tvdb", raising_ctor)
    factory = PosterServiceFactory(_config_service_all_enabled())

    services = factory.get_configured_services()

    assert {s.name for s in services} == ALL_PROVIDERS - {"tvdb"}

def test_unconfigured_provider_is_skipped(monkeypatch):
    monkeypatch.setattr(tvdb_mod, "TVDB", MagicMock())
    svc = _config_service_all_enabled()
    svc.configs["tvdb"] = None

    factory = PosterServiceFactory(svc)
    services = factory.get_configured_services()

    assert {s.name for s in services} == ALL_PROVIDERS - {"tvdb"}

def test_disabled_provider_is_skipped(monkeypatch):
    monkeypatch.setattr(tvdb_mod, "TVDB", MagicMock())
    svc = _config_service_all_enabled()
    disabled = _provider_config("tvdb")
    disabled.enabled = False
    svc.configs["tvdb"] = disabled

    services = PosterServiceFactory(svc).get_configured_services()

    assert {s.name for s in services} == ALL_PROVIDERS - {"tvdb"}

def test_empty_token_provider_is_skipped(monkeypatch):
    monkeypatch.setattr(tvdb_mod, "TVDB", MagicMock())
    svc = _config_service_all_enabled()
    blank = _provider_config("tvdb")
    blank.token = ""
    svc.configs["tvdb"] = blank

    services = PosterServiceFactory(svc).get_configured_services()

    assert {s.name for s in services} == ALL_PROVIDERS - {"tvdb"}

def test_needing_no_key_is_opt_in():
    assert ExternalProvider.requires_api_key is True
    open_apis = {name for name, cls in EXTERNAL_PROVIDERS.items() if not cls.requires_api_key}
    assert open_apis == {"tvmaze"}

def test_open_api_provider_is_built_without_a_token(monkeypatch):
    monkeypatch.setitem(factory_mod.EXTERNAL_PROVIDERS, "tvdb", _OpenApiClient)
    svc = _config_service_all_enabled()
    keyless = _provider_config("tvdb")
    keyless.token = ""
    svc.configs["tvdb"] = keyless

    services = PosterServiceFactory(svc).get_configured_services()

    assert {s.name for s in services} == (ALL_PROVIDERS - {"tvdb"}) | {"open"}

def test_an_open_api_provider_still_honours_enabled(monkeypatch):
    monkeypatch.setitem(factory_mod.EXTERNAL_PROVIDERS, "tvdb", _OpenApiClient)
    svc = _config_service_all_enabled()
    keyless = _provider_config("tvdb")
    keyless.token = ""
    keyless.enabled = False
    svc.configs["tvdb"] = keyless

    services = PosterServiceFactory(svc).get_configured_services()

    assert {s.name for s in services} == ALL_PROVIDERS - {"tvdb"}

def test_a_provider_with_no_stored_url_is_skipped(monkeypatch):
    monkeypatch.setattr(tvdb_mod, "TVDB", MagicMock())
    svc = _config_service_all_enabled()
    svc.configs["fanart"] = _provider_config("fanart", url="")

    services = PosterServiceFactory(svc).get_configured_services()

    assert {s.name for s in services} == ALL_PROVIDERS - {"fanart"}

def test_tvdb_is_built_without_a_url(monkeypatch):
    monkeypatch.setattr(tvdb_mod, "TVDB", MagicMock())
    svc = _config_service_all_enabled()
    svc.configs["tvdb"] = _provider_config("tvdb", url="")

    services = PosterServiceFactory(svc).get_configured_services()

    assert "tvdb" in {s.name for s in services}

def test_the_stored_url_is_what_the_client_calls(monkeypatch):
    monkeypatch.setattr(tvdb_mod, "TVDB", MagicMock())
    svc = _config_service_all_enabled()
    svc.configs["tvmaze"] = _provider_config("tvmaze", url="https://mirror.example/")

    tvmaze = next(s for s in PosterServiceFactory(svc).get_configured_services()
                  if s.name == "tvmaze")

    assert tvmaze.base_url == "https://mirror.example"
