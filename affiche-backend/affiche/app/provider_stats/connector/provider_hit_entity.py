from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from affiche.config import Base

class ProviderHitEntity(Base):
    __tablename__ = "provider_hit"
    __table_args__ = (
        UniqueConstraint('day', 'provider', 'library_id', name='uq_provider_hit_day_provider_library'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    library_id: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
