from typing import List, Optional

from affiche.app.service_configuration.model.service_configuration import ServiceConfiguration, ServiceType
from affiche.app.service_configuration.service.configuration_repository import ConfigurationRepository

class ServiceConfigurationService:

    def __init__(self, repository: ConfigurationRepository):
        self._repository = repository

    def save(self, service_configuration: ServiceConfiguration,
             keep_existing_token: bool = False):
        if keep_existing_token:
            existing = self._repository.get_service_configuration(service_configuration.name)
            if existing:
                service_configuration = service_configuration.model_copy(
                    update={"token": existing.token})
        return self._repository.save(service_configuration)

    def get_config(self, key: str) -> Optional[ServiceConfiguration]:
        return self._repository.get_service_configuration(key)

    def find_configs(self, type: Optional[ServiceType] = None) -> List[ServiceConfiguration]:
        return self._repository.find_service_configurations(type)

    def delete_config(self, key: str) -> bool:
        return self._repository.delete(key)
