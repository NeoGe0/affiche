from typing import Optional

from pydantic import BaseModel

from affiche.app.auth.model.user import UserRole

class SetupRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.OPERATOR

class UpdateUserRequest(BaseModel):
    role: UserRole

class UserAccountResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    password_change_required: bool = False

class UserResponse(BaseModel):
    username: str
    role: UserRole = UserRole.ADMIN
    password_change_required: bool = False

class AuthStatusResponse(BaseModel):
    setup_required: bool
    authenticated: bool
    username: Optional[str] = None
    role: Optional[UserRole] = None
    password_change_required: bool = False
