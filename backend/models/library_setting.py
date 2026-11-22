
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Integer,
    Numeric,
    DateTime,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class LibrarySetting(Base):
    __tablename__ = "library_settings"

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_library_settings_single_row"
        ),
        CheckConstraint(
            "loan_period_days > 0",
            name="ck_settings_loan_period"
        ),
        CheckConstraint(
            "fine_per_day >= 0",
            name="ck_settings_fine_per_day"
        ),
        CheckConstraint(
            "max_fine_amount >= 0",
            name="ck_settings_max_fine"
        ),
        CheckConstraint(
            "max_active_loans > 0",
            name="ck_settings_max_loans"
        ),
        CheckConstraint(
            "hold_period_hours > 0",
            name="ck_settings_hold_period"
        ),
        CheckConstraint(
            "fine_block_threshold >= 0",
            name="ck_settings_fine_threshold"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1
    )

    loan_period_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=14
    )

    fine_per_day: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("5.00")
    )

    max_fine_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("100.00")
    )

    max_active_loans: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3
    )

    hold_period_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24
    )

    fine_block_threshold: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("50.00")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
