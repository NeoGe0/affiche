from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from affiche.config import Base

class LibraryEpisodeEntity(Base):

    __tablename__ = "library_episode"
    __table_args__ = (
        UniqueConstraint('external_id', 'season_id', 'library_id',
                         name='uq_library_episode_external_season_library'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("library_season.id", ondelete='CASCADE'), nullable=False)
    show_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("library_item.id", ondelete='CASCADE'), nullable=False)
    library_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("library.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(250), nullable=False)

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    air_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    imdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tmdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tvdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    media_resolution: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    media_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audio_codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audio_channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_container: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    media_bitrate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    media_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
