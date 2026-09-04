from typing import List, Optional

from sqlalchemy.orm import Session

from affiche.app.auth.connector.user_connector import UserConnector
from affiche.app.auth.model.user import User, UserRole

class UserRepository:

    def __init__(self, session: Session):
        self._connector = UserConnector(session)

    def get_by_username(self, username: str) -> Optional[User]:
        entity = self._connector.get_by_username(username)
        if entity is None:
            return None
        return User.model_validate(entity)

    def count(self) -> int:
        return self._connector.count()

    def find_all(self) -> List[User]:
        return [User.model_validate(entity) for entity in self._connector.find_all()]

    def count_admins(self) -> int:
        return self._connector.count_admins()

    def delete(self, user_id: int) -> bool:
        return self._connector.delete(user_id)

    def create(self, username: str, password_hash: str,
               role: UserRole = UserRole.ADMIN) -> User:
        entity = self._connector.create(username, password_hash, role)
        return User.model_validate(entity)

    def set_password(self, user_id: int, password_hash: str, temporary: bool) -> Optional[User]:
        entity = self._connector.set_password(user_id, password_hash, temporary)
        return User.model_validate(entity) if entity else None

    def set_role(self, user_id: int, role: UserRole) -> Optional[User]:
        entity = self._connector.set_role(user_id, role)
        return User.model_validate(entity) if entity else None

    def find_first(self) -> Optional[User]:
        entity = self._connector.find_first()
        return User.model_validate(entity) if entity else None

    def increment_token_version(self, user_id: int) -> Optional[User]:
        entity = self._connector.increment_token_version(user_id)
        return User.model_validate(entity) if entity else None
