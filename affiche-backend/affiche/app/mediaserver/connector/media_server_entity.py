import json
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, String, Enum, text
from sqlalchemy.orm import Mapped, mapped_column

from affiche.app.encryption.encryption import EncryptedString
from affiche.app.mediaserver.model.media_server import MediaServerType
from affiche.config import Base
from affiche.config.env_config import get_encryption_key
from affiche.config.language_config import DEFAULT_LANGUAGE_ORDER

class MediaServerEntity(Base):
    __tablename__ = "media_server"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[MediaServerType] = mapped_column(Enum(MediaServerType), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    token: Mapped[str] = mapped_column(
        EncryptedString(key_provider=get_encryption_key),
        nullable=False
    )

    enabled: Mapped[bool] = mapped_column(default=True)
    language_order: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: list(DEFAULT_LANGUAGE_ORDER),
        server_default=text(f"'{json.dumps(DEFAULT_LANGUAGE_ORDER)}'"),
    )
    fallback_to_server_poster: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"))
    skip_style_when_not_textless: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"))
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    last_sync: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
