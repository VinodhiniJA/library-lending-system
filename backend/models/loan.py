
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


class Loan(Base):
    __tablename__ = "loans"

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'RETURNED')",
            name="ck_loans_status"
        ),
        CheckConstraint(
            "due_at > borrowed_at",
            name="ck_loans_due_after_borrowed"
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND returned_at IS NULL) OR "
            "(status = 'RETURNED' AND returned_at IS NOT NULL)",
            name="ck_loans_return_status"
        ),
        Index(
            "uq_loans_one_active_per_copy",
            "copy_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'")
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

    copy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("book_copies.id"),
        nullable=False
    )

    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE"
    )

    user = relationship("User", back_populates="loans")
    copy = relationship("BookCopy", back_populates="loans")
    fine = relationship("Fine", back_populates="loan", uselist=False)
