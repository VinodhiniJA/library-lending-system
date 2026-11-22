
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column,  relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class Book(Base):
    __tablename__ = "books"

    __table_args__ = (
        CheckConstraint(
            "total_copies >= 0",
            name="ck_books_total_copies"
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_books_title_not_empty"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    author: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    total_copies: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    copies = relationship("BookCopy", back_populates="book")
    reservations = relationship("Reservation", back_populates="book")