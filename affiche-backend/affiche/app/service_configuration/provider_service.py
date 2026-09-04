import logging

from affiche.app.service_configuration.exceptions import UnknownProviderError, ProviderConnectionError
from affiche.external.poster.provider import (
    TMDBClient,
    TVDBClient,
    FanartClient,
    MediuxClient,
    TVmazeClient,
    ShokoClient,
)

EXTERNAL_PROVIDERS = {
    "tmdb": TMDBClient,
    "tvdb": TVDBClient,
    "fanart": FanartClient,
    "mediux": MediuxClient,
    "tvmaze": TVmazeClient,
    "shoko": ShokoClient,
}

logger = logging.getLogger(__name__)

class ProviderService:

    def test_provider_api_token(self, provider: str, api_token: str, url: str = "") -> dict:
        provider_class = EXTERNAL_PROVIDERS.get(provider.lower())
        if not provider_class:
            raise UnknownProviderError(provider, list(EXTERNAL_PROVIDERS.keys()))

        if not api_token and provider_class.requires_api_key:
            raise ProviderConnectionError(provider)

        kwargs = {"api_key": api_token}
        if provider_class.uses_base_url():
            if not url:
                raise ProviderConnectionError(provider)
            kwargs["base_url"] = url

        try:
            client = provider_class(**kwargs)
            success = client.test_connection(api_token)

            if success:
                return {
                    "status": "success",
                    "message": f"Connected to {provider.upper()} successfully"
                }
            else:
                raise ProviderConnectionError(provider)
        except ProviderConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error testing {provider} connection: {e}")
            raise ProviderConnectionError(provider)
