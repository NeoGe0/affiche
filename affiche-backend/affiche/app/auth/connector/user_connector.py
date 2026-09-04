from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from affiche.app.auth.connector.user_entity import UserEntity
from affiche.app.auth.model.user import UserRole

class UserConnector:

    def __init__(self, session: Session):
        self._session = session

    def get_by_username(self, username: str) -> Optional[UserEntity]:
        stmt = select(UserEntity).where(UserEntity.username == username)
        return self._session.scalars(stmt).first()

    def count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(UserEntity)) or 0

    def find_all(self) -> List[UserEntity]:
        return list(self._session.scalars(select(UserEntity).order_by(UserEntity.id)).all())

    def count_admins(self) -> int:
        stmt = select(func.count()).select_from(UserEntity).where(UserEntity.role == UserRole.ADMIN)
        return self._session.scalar(stmt) or 0

    def delete(self, user_id: int) -> bool:
        entity = self._session.get(UserEntity, user_id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True

    def create(self, username: str, password_hash: str,
               role: UserRole = UserRole.ADMIN) -> UserEntity:
        entity = UserEntity(username=username, password_hash=password_hash, role=role)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def set_password(self, user_id: int, password_hash: str,
                     temporary: bool) -> Optional[UserEntity]:
        entity = self._session.get(UserEntity, user_id)
        if entity is None:
            return None
        entity.password_hash = password_hash
        entity.password_temporary = temporary
        entity.token_version = (entity.token_version or 0) + 1
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def set_role(self, user_id: int, role: UserRole) -> Optional[UserEntity]:
        entity = self._session.get(UserEntity, user_id)
        if entity is None:
            return None
        entity.role = role
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def find_first(self) -> Optional[UserEntity]:
        return self._session.scalars(select(UserEntity).order_by(UserEntity.id)).first()

    def increment_token_version(self, user_id: int) -> Optional[UserEntity]:
        entity = self._session.get(UserEntity, user_id)
        if entity is None:
            return None
        entity.token_version = (entity.token_version or 0) + 1
        self._session.commit()
        self._session.refresh(entity)
        return entity
