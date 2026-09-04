import pytest

from affiche.app.service_configuration.exceptions import (
    ProviderConnectionError,
    UnknownProviderError,
)
from affiche.app.service_configuration.provider_service import EXTERNAL_PROVIDERS, ProviderService
from affiche.external.poster.provider.base_provider import BaseUrlMode

def test_an_empty_token_is_refused_without_spending_a_request(monkeypatch):
    called = False

    def spy(self, api_token):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(EXTERNAL_PROVIDERS["fanart"], "test_connection", spy)

    with pytest.raises(ProviderConnectionError):
        ProviderService().test_provider_api_token("fanart", "")

    assert called is False

def test_an_open_api_provider_is_tested_with_no_token(monkeypatch):
    monkeypatch.setitem(EXTERNAL_PROVIDERS, "open", _OpenApiClient)

    result = ProviderService().test_provider_api_token("open", "")

    assert result["status"] == "success"

def test_an_open_api_provider_that_is_unreachable_still_fails(monkeypatch):
    class Unreachable(_OpenApiClient):
        def test_connection(self, api_token) -> bool:
            return False

    monkeypatch.setitem(EXTERNAL_PROVIDERS, "open", Unreachable)

    with pytest.raises(ProviderConnectionError):
        ProviderService().test_provider_api_token("open", "")

def test_an_unknown_provider_is_still_rejected_before_the_token_check():
    with pytest.raises(UnknownProviderError):
        ProviderService().test_provider_api_token("nope", "")

class _OpenApiClient:

    requires_api_key = False
    base_url_mode = BaseUrlMode.NONE

    @classmethod
    def uses_base_url(cls) -> bool:
        return False

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def test_connection(self, api_token) -> bool:
        return True
