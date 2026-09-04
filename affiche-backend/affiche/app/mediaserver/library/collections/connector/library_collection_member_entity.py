from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from affiche.config import Base

class LibraryCollectionMemberEntity(Base):
    __tablename__ = "library_collection_item"

    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("library_collection.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("library_item.id", ondelete="CASCADE"), primary_key=True
    )
