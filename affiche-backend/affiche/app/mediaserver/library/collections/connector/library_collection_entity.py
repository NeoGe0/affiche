from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from affiche.config import Base

class LibraryCollectionEntity(Base):
    __tablename__ = "library_collection"
    __table_args__ = (
        UniqueConstraint('external_id', 'library_id', name='uq_library_collection_external_library'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(250), nullable=False)
    library_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("library.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    sort_title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    child_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    poster_uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    poster_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    poster_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    poster_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    tmdb_collection_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    processed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[bool] = mapped_column(default=False, server_default=false(), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
