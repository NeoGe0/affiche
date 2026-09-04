from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from affiche.config import Base

if TYPE_CHECKING:
    from affiche.app.mediaserver.library.settings.connector.library_settings_entity import LibrarySettingsEntity

class LibraryEntity(Base):
    __tablename__ = "library"
    __table_args__ = (
        UniqueConstraint('external_id', 'media_server_id', name='uq_library_external_media_server'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_server_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("media_server.id", ondelete="CASCADE"),
        nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(250), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    uuid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    settings: Mapped["LibrarySettingsEntity | None"] = relationship(
        back_populates="library",
        uselist=False,
        cascade="all, delete-orphan"
    )
