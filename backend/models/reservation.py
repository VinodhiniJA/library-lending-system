
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class Reservation(Base):
    __tablename__ = "reservations"

    __table_args__ = (
        CheckConstraint(
            "status IN ('WAITING', 'HELD', 'FULFILLED', 'EXPIRED', 'CANCELLED')",
            name="ck_reservations_status"
        ),
        CheckConstraint(
            "(status = 'HELD' AND copy_id IS NOT NULL "
            "AND hold_expires_at IS NOT NULL) OR "
            "(status != 'HELD')",
            name="ck_reservations_hold_fields"
        ),
        Index(
            "ix_reservations_waiting_queue",
            "book_id",
            "created_at",
            "id",
            postgresql_where=text("status = 'WAITING'")
        ),
        Index(
            "uq_reservations_one_held_per_copy",
            "copy_id",
            unique=True,
            postgresql_where=text("status = 'HELD'")
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id"),
        nullable=False
    )

    copy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("book_copies.id"),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="WAITING"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    hold_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    user = relationship("User", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")
    copy = relationship("BookCopy", back_populates="reservations")
