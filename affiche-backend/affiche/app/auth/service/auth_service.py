import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import bcrypt
from jose import JWTError, jwt

from affiche.app.auth.model.user import User, UserRole
from affiche.app.auth.service.user_repository import UserRepository
from affiche.config.env_config import get_auth_secret

logger = logging.getLogger(__name__)

_JWT_ALGORITHM = "HS256"
_TOKEN_VERSION_CLAIM = "ver"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
SESSION_COOKIE_NAME = "affiche_session"

_BCRYPT_MAX_BYTES = 72

_TEMPORARY_PASSWORD_BYTES = 12

MIN_PASSWORD_LENGTH = 8

def _hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")

def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8")[:_BCRYPT_MAX_BYTES],
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False

class AuthError(Exception):
    pass

class AuthService:

    def __init__(self, repository: UserRepository):
        self._repository = repository

    def has_admin(self) -> bool:
        return self._repository.count() > 0

    def create_admin(self, username: str, password: str) -> User:
        username = (username or "").strip()
        if not username:
            raise AuthError("Username is required")
        if not password:
            raise AuthError("Password is required")
        if self.has_admin():
            raise AuthError("An admin account already exists")
        return self._repository.create(username, _hash_password(password))

    def reset_password(self, username: Optional[str] = None) -> Tuple[str, str]:
        user = (self._repository.get_by_username((username or "").strip()) if username
                else self._repository.find_first())
        if user is None:
            raise AuthError(f"No account named {username!r}" if username
                            else "No account exists yet — open the app and run first-run setup")

        password = secrets.token_urlsafe(_TEMPORARY_PASSWORD_BYTES)
        self._repository.set_password(user.id, _hash_password(password), temporary=True)
        logger.warning("Password reset for %r via the CLI; every session was signed out",
                       user.username)
        return user.username, password

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not _verify_password(current_password, user.password_hash):
            raise AuthError("Current password is incorrect")
        if len(new_password or "") < MIN_PASSWORD_LENGTH:
            raise AuthError(f"New password must be at least {MIN_PASSWORD_LENGTH} characters")
        if new_password == current_password:
            raise AuthError("New password must be different from the current one")

        updated = self._repository.set_password(
            user.id, _hash_password(new_password), temporary=False)
        logger.info("Password changed for %r; every other session was signed out", user.username)
        return updated

    def list_users(self) -> List[User]:
        return self._repository.find_all()

    def create_user(self, username: str, password: str, role: UserRole) -> User:
        username = (username or "").strip()
        if not username:
            raise AuthError("Username is required")
        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        if self._repository.get_by_username(username) is not None:
            raise AuthError(f"An account named {username!r} already exists")
        return self._repository.create(username, _hash_password(password), role)

    def set_role(self, user_id: int, role: UserRole, acting_user: User) -> User:
        target = next((u for u in self._repository.find_all() if u.id == user_id), None)
        if target is None:
            raise AuthError("No such account")
        if target.id == acting_user.id:
            raise AuthError("You cannot change your own role")
        updated = self._repository.set_role(user_id, role)
        logger.info("Account %r is now %s", target.username, role.value)
        return updated

    def delete_user(self, user_id: int, acting_user: User) -> None:
        target = next((u for u in self._repository.find_all() if u.id == user_id), None)
        if target is None:
            raise AuthError("No such account")
        if target.id == acting_user.id:
            raise AuthError("You cannot delete your own account")
        if target.role == UserRole.ADMIN and self._repository.count_admins() <= 1:
            raise AuthError("The last administrator cannot be deleted")
        self._repository.delete(user_id)
        logger.info("Deleted account %r", target.username)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self._repository.get_by_username((username or "").strip())
        if user is None:
            return None
        if not _verify_password(password, user.password_hash):
            return None
        return user

    def issue_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.username,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=SESSION_TTL_SECONDS)).timestamp()),
            _TOKEN_VERSION_CLAIM: user.token_version,
        }
        return jwt.encode(payload, get_auth_secret(), algorithm=_JWT_ALGORITHM)

    def user_from_token(self, token: str) -> Optional[User]:
        if not token:
            return None
        try:
            payload = jwt.decode(token, get_auth_secret(), algorithms=[_JWT_ALGORITHM])
        except JWTError:
            return None
        username = payload.get("sub")
        if not username:
            return None
        user = self._repository.get_by_username(username)
        if user is None:
            return None
        if payload.get(_TOKEN_VERSION_CLAIM, 0) != user.token_version:
            return None
        return user

    def revoke_sessions(self, token: Optional[str]) -> bool:
        user = self.user_from_token(token)
        if user is None:
            return False
        self._repository.increment_token_version(user.id)
        logger.info("Revoked sessions for %r", user.username)
        return True
