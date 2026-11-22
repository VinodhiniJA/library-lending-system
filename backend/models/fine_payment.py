
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class FinePayment(Base):
    __tablename__ = "fine_payments"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_fine_payments_positive_amount"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    fine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fines.id"),
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    fine = relationship("Fine", back_populates="payments")
