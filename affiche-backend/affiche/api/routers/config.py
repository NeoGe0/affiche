from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from affiche.api.schemas.api_schemas import (
    ServiceConfigurationCreate,
    ServiceConfigurationResponse,
    ServiceConfigurationType,
)
from affiche.app.service_configuration.model.service_configuration import (
    ServiceConfiguration,
    ServiceType,
)
from affiche.config.dependencies import get_service_configuration_service

router = APIRouter()

@router.get("", response_model=List[ServiceConfigurationResponse])
def find_configs(type: Optional[ServiceConfigurationType] = None,
                 service=Depends(get_service_configuration_service)) -> List[ServiceConfigurationResponse]:
    configs = service.find_configs(ServiceType(type.value) if type else None)
    return [ServiceConfigurationResponse.from_domain(config) for config in configs]

@router.get("/{key}", response_model=Optional[ServiceConfigurationResponse])
def get_config(key: str, service=Depends(get_service_configuration_service)) -> Optional[ServiceConfigurationResponse]:
    config = service.get_config(key)
    return ServiceConfigurationResponse.from_domain(config) if config else None

@router.post("/", response_model=ServiceConfigurationResponse)
def save_config(config: ServiceConfigurationCreate,
                service=Depends(get_service_configuration_service)) -> ServiceConfigurationResponse:
    keep_existing_token = config.token is None
    dto = ServiceConfiguration.model_validate({**config.model_dump(), "token": config.token or ""})
    return ServiceConfigurationResponse.from_domain(
        service.save(dto, keep_existing_token=keep_existing_token))

@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(key: str, service=Depends(get_service_configuration_service)):
    if not service.delete_config(key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No configuration for '{key}'")
