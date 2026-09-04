from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Boolean, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from affiche.app.mediaserver.library.connector.library_entity import LibraryEntity
from affiche.config import Base
from affiche.config.library_config import DEFAULT_PROVIDER_ORDER

class LibrarySettingsEntity(Base):
    __tablename__ = "library_settings"

    library_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("library.id", ondelete="CASCADE"),
        primary_key=True
    )
    upload_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    provider_order: Mapped[list[str]] = mapped_column(
        JSON,
        default=DEFAULT_PROVIDER_ORDER
    )
    overlay_options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    text_options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    style_profile_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("style_profile.id", ondelete="SET NULL"),
        nullable=True
    )

    track_episodes: Mapped[bool] = mapped_column(Boolean, default=False)
    track_collections: Mapped[bool] = mapped_column(Boolean, default=False,
                                                    server_default=false(), nullable=False)
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=360)
    auto_pickup_action: Mapped[str] = mapped_column(String(20), default="sync")
    last_auto_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_full_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    library: Mapped[LibraryEntity] = relationship(back_populates="settings")
