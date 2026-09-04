import logging
from typing import Optional, List, Type

from affiche.app.service_configuration.model.service_configuration import ServiceConfiguration
from affiche.app.service_configuration.provider_service import EXTERNAL_PROVIDERS
from affiche.app.service_configuration.service.service_configuration_service import ServiceConfigurationService
from affiche.external.poster.provider import ExternalProvider

logger = logging.getLogger(__name__)

class PosterServiceFactory:

    def __init__(self, config_service: ServiceConfigurationService):

        self.config_service = config_service

    def get_configured_services(self) -> List[ExternalProvider]:
        services: List[ExternalProvider] = []
        for name in EXTERNAL_PROVIDERS:
            try:
                service = self.get_service(name)
            except Exception:
                logger.exception("Failed to construct a poster provider; skipping it")
                continue
            if service is not None:
                services.append(service)
        return services

    def get_service(self, name: str) -> Optional[ExternalProvider]:
        provider_class = EXTERNAL_PROVIDERS.get(name)
        if provider_class is None:
            return None

        config = self.config_service.get_config(name)
        if not self._is_configured(config, provider_class):
            logger.warning("%s is not configured or enabled", name)
            return None

        if provider_class.uses_base_url():
            return provider_class(api_key=config.token, base_url=config.url)
        return provider_class(api_key=config.token)

    def _is_configured(self,
                       config: ServiceConfiguration,
                       provider_class: Type[ExternalProvider]) -> bool:
        if not (config and config.enabled):
            return False
        if provider_class.uses_base_url() and not config.url:
            return False
        return bool(config.token) or not provider_class.requires_api_key
