from datetime import datetime, timezone

from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column

from affiche.app.encryption.encryption import EncryptedString
from affiche.app.service_configuration.model.service_configuration import ServiceType
from affiche.config import Base
from affiche.config.env_config import get_encryption_key

class ServiceConfigurationEntity(Base):
    __tablename__ = "service_configuration"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    type: Mapped[ServiceType] = mapped_column(Enum(ServiceType), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    token: Mapped[str] = mapped_column(
        EncryptedString(key_provider=get_encryption_key),
        nullable=False
    )

    enabled: Mapped[bool] = mapped_column(default=True)
    last_verified: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
