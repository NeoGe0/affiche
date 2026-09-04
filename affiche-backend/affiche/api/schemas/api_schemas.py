from enum import Enum
from typing import Optional

from pydantic import BaseModel

from affiche.app.service_configuration.model.service_configuration import ServiceConfiguration

class ServiceConfigurationType(str, Enum):
    LIBRARY = "LIBRARY"
    PROVIDER = "PROVIDER"

TOKEN_HINT_CHARS = 4

def token_hint(token: Optional[str]) -> Optional[str]:
    if not token or len(token) <= TOKEN_HINT_CHARS:
        return None
    return token[-TOKEN_HINT_CHARS:]

class ServiceConfigurationCreate(BaseModel):
    name: str
    type: ServiceConfigurationType
    url: str
    token: Optional[str] = None
    enabled: bool

class ServiceConfigurationResponse(BaseModel):
    name: str
    type: ServiceConfigurationType
    url: str
    enabled: bool
    configured: bool
    token_hint: Optional[str] = None

    @classmethod
    def from_domain(cls, config: ServiceConfiguration) -> "ServiceConfigurationResponse":
        return cls(
            name=config.name,
            type=config.type,
            url=config.url,
            enabled=config.enabled,
            configured=bool(config.token),
            token_hint=token_hint(config.token),
        )
