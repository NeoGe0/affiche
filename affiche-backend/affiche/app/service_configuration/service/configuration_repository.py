from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.service_configuration.connector.configuration_connector import ConfigurationConnector
from affiche.app.service_configuration.model.service_configuration import ServiceConfiguration, ServiceType

class ConfigurationRepository:

    def __init__(self, session: Session):
        self._connector = ConfigurationConnector(session)

    def get_service_configuration(self, name: str) -> Optional[ServiceConfiguration]:
        configuration = self._connector.get_configuration(name)
        if configuration is None:
            return None
        return ServiceConfiguration.model_validate(configuration)

    def find_service_configurations(self, type: Optional[ServiceType] = None) -> List[ServiceConfiguration]:
        configurations = self._connector.find_configurations(type)
        return [ServiceConfiguration.model_validate(configuration) for configuration in configurations]

    def delete(self, name: str) -> bool:
        return self._connector.delete_configuration(name)

    def save(self, service_configuration: ServiceConfiguration) -> ServiceConfiguration:
        configuration = self._connector.upsert_configuration(service_configuration)
        return ServiceConfiguration.model_validate(configuration)
