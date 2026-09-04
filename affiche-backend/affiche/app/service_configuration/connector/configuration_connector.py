from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from affiche.app.service_configuration.connector.service_configuration_entity import ServiceConfigurationEntity
from affiche.app.service_configuration.model.service_configuration import ServiceConfiguration, ServiceType

class ConfigurationConnector:

    def __init__(self, session: Session):
        self._session = session

    def get_configuration(self, name: str) -> Optional[ServiceConfigurationEntity]:
        entity = (self._session.query(ServiceConfigurationEntity)
                .where(ServiceConfigurationEntity.name == name)
                .first())
        return entity

    def find_configurations(self, type: Optional[ServiceType] = None) -> List[ServiceConfigurationEntity]:
        stmt = select(ServiceConfigurationEntity)
        if type is not None:
            stmt = stmt.where(ServiceConfigurationEntity.type == type)
        return list(self._session.scalars(stmt).all())

    def delete_configuration(self, name: str) -> bool:
        entity = self.get_configuration(name)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True

    def upsert_configuration(self, service_configuration: ServiceConfiguration) -> ServiceConfigurationEntity:
        entity = self.get_configuration(service_configuration.name)
        if entity is None:
            entity = ServiceConfigurationEntity(name=service_configuration.name)
            self._session.add(entity)

        entity.type = service_configuration.type
        entity.url = service_configuration.url
        entity.token = service_configuration.token
        entity.enabled = service_configuration.enabled

        self._session.commit()
        self._session.refresh(entity)
        return entity
