from enum import Enum

from pydantic import BaseModel, ConfigDict

class ServiceType(str, Enum):
    LIBRARY = "LIBRARY"
    PROVIDER = "PROVIDER"

class ServiceConfiguration(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    type: ServiceType
    token: str
    url: str
    enabled: bool
