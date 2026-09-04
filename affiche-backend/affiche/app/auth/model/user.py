from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    password_hash: str
    role: UserRole = UserRole.ADMIN
    token_version: int = 0
    password_temporary: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
