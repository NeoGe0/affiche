from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, BigInteger, Text, ForeignKey, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from affiche.config import Base

class LibraryItemEntity(Base):
    __tablename__ = "library_item"
    __table_args__ = (
        UniqueConstraint('external_id', 'library_id', name='uq_library_item_external_library'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(250), nullable=False)
    library_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("library.id", ondelete="CASCADE"),
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    release_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    poster_uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    imdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tmdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tvdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    poster_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    poster_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    poster_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    style_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    media_resolution: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    media_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audio_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audio_channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_container: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    processed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[bool] = mapped_column(default=False, server_default=false(), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

