
from datetime import datetime, timezone
from decimal import Decimal, ROUND_UP
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.loan import Loan
from models.fine import Fine
from models.fine_payment import FinePayment
from models.library_setting import LibrarySetting


def calculate_fine(
    due_at: datetime,
    returned_at: datetime | None,
    fine_per_day: Decimal,
    max_fine_amount: Decimal,
    now: datetime | None = None
) -> Decimal:
    """Calculate overdue fines with a maximum cap."""

    if now is None:
        now = datetime.now(timezone.utc)

    end_time = returned_at if returned_at is not None else now

    # Normalize timestamps to naive UTC
    if due_at.tzinfo is not None:
        due_at = due_at.astimezone(
            timezone.utc
        ).replace(tzinfo=None)

    if end_time.tzinfo is not None:
        end_time = end_time.astimezone(
            timezone.utc
        ).replace(tzinfo=None)

    if end_time <= due_at:
        return Decimal("0.00")

    overdue_seconds = Decimal(
        str((end_time - due_at).total_seconds())
    )

    overdue_days = int(
        (overdue_seconds / Decimal("86400"))
        .to_integral_value(rounding=ROUND_UP)
    )

    fine_amount = (
        Decimal(overdue_days) * Decimal(fine_per_day)
    )

    return min(
        fine_amount,
        Decimal(max_fine_amount)
    ).quantize(Decimal("0.01"))


def assess_loan_fine(
    db: Session,
    loan: Loan,
    now: datetime | None = None
):
    """Create or update the fine for an overdue loan."""

    settings = db.get(LibrarySetting, 1)

    if settings is None:
        raise HTTPException(
            status_code=500,
            detail="Library settings are not configured"
        )

    amount = calculate_fine(
        due_at=loan.due_at,
        returned_at=loan.returned_at,
        fine_per_day=Decimal(settings.fine_per_day),
        max_fine_amount=Decimal(settings.max_fine_amount),
        now=now
    )

    fine = db.scalar(
        select(Fine)
        .where(Fine.loan_id == loan.id)
        .with_for_update()
    )

    if fine is None:
        if amount == Decimal("0.00"):
            return None

        fine = Fine(
            loan_id=loan.id,
            amount=amount
        )

        db.add(fine)

    else:
        # Preserve amounts already assessed or paid
        paid_amount = Decimal(
            db.scalar(
                select(
                    func.coalesce(
                        func.sum(FinePayment.amount),
                        0
                    )
                ).where(FinePayment.fine_id == fine.id)
            )
        )

        fine.amount = max(
            Decimal(fine.amount),
            amount,
            paid_amount
        )

    db.flush()
    return fine


def get_outstanding_fines(
    db: Session,
    user_id: UUID
) -> Decimal:
    """Calculate a member's unpaid fine balance."""

    total_fines = db.scalar(
        select(
            func.coalesce(func.sum(Fine.amount), 0)
        )
        .join(Loan, Fine.loan_id == Loan.id)
        .where(Loan.user_id == user_id)
    )

    total_payments = db.scalar(
        select(
            func.coalesce(func.sum(FinePayment.amount), 0)
        )
        .join(Fine, FinePayment.fine_id == Fine.id)
        .join(Loan, Fine.loan_id == Loan.id)
        .where(Loan.user_id == user_id)
    )

    outstanding = (
        Decimal(total_fines) - Decimal(total_payments)
    )

    return max(
        Decimal("0.00"),
        outstanding
    )
