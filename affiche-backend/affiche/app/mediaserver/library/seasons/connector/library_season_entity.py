from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from affiche.config import Base

class LibrarySeasonEntity(Base):

    __tablename__ = "library_season"
    __table_args__ = (
        UniqueConstraint('external_id', 'show_id', 'library_id', name='uq_library_season_external_show_library'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    show_id: Mapped[int] = mapped_column(Integer, ForeignKey("library_item.id", ondelete='CASCADE'), nullable=False)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("library.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(250), nullable=False)

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    imdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tmdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tvdb_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    poster_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    poster_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    poster_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    style_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    processed: Mapped[bool] = mapped_column(default=False)
