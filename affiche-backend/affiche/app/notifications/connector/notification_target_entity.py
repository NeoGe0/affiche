from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from affiche.app.encryption.encryption import EncryptedString
from affiche.app.notifications.model.notification_target import NotificationType
from affiche.config import Base
from affiche.config.env_config import get_encryption_key

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class NotificationTargetEntity(Base):
    __tablename__ = "notification_target"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    url: Mapped[str] = mapped_column(
        EncryptedString(key_provider=get_encryption_key),
        nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("1"),
                                          nullable=False)
    on_task_completed: Mapped[bool] = mapped_column(Boolean, default=True,
                                                    server_default=text("1"), nullable=False)
    on_task_failed: Mapped[bool] = mapped_column(Boolean, default=True,
                                                 server_default=text("1"), nullable=False)
    on_items_errored: Mapped[bool] = mapped_column(Boolean, default=True,
                                                   server_default=text("1"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
