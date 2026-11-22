
import uuid

from sqlalchemy import String, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class BookCopy(Base):
    __tablename__ = "book_copies"

    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'BORROWED', 'HELD')",
            name="ck_book_copies_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="AVAILABLE"
    )

    book = relationship("Book", back_populates="copies")
    loans = relationship("Loan", back_populates="copy")
    reservations = relationship("Reservation", back_populates="copy")
