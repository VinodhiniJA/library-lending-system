
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


class Fine(Base):
    __tablename__ = "fines"

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="ck_fines_amount_nonnegative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loans.id"),
        unique=True,
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    loan = relationship("Loan", back_populates="fine")
    payments = relationship("FinePayment", back_populates="fine")
