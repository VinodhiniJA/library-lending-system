
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.fine import Fine
from models.fine_payment import FinePayment
from models.loan import Loan
from services.fine_service import assess_loan_fine


def get_member_fines(db: Session, user_id: UUID):
    # Refresh fines for currently overdue active loans
    overdue_loans = db.scalars(
        select(Loan).where(
            Loan.user_id == user_id,
            Loan.status == "ACTIVE"
        )
    ).all()

    for loan in overdue_loans:
        assess_loan_fine(db, loan)

    db.commit()

    fines = db.scalars(
        select(Fine)
        .join(Loan, Fine.loan_id == Loan.id)
        .where(Loan.user_id == user_id)
    ).all()

    results = []

    for fine in fines:
        paid = db.scalar(
            select(func.coalesce(func.sum(FinePayment.amount), 0))
            .where(FinePayment.fine_id == fine.id)
        )

        paid = Decimal(paid)

        results.append({
            "id": fine.id,
            "loan_id": fine.loan_id,
            "amount": fine.amount,
            "paid_amount": paid,
            "outstanding_amount": max(
                Decimal("0.00"),
                fine.amount - paid
            )
        })

    return results


def record_fine_payment(
    db: Session,
    fine_id: UUID,
    amount: Decimal
):
    try:
        # Lock fine to serialize payment requests
        fine = db.scalar(
            select(Fine)
            .where(Fine.id == fine_id)
            .with_for_update()
        )

        if fine is None:
            raise HTTPException(
                status_code=404,
                detail="Fine not found"
            )

        loan = db.get(Loan, fine.loan_id)

        # Refresh an active loan's accrued fine
        if loan.status == "ACTIVE":
            assess_loan_fine(db, loan)

        total_paid = Decimal(
            db.scalar(
                select(
                    func.coalesce(
                        func.sum(FinePayment.amount), 0
                    )
                ).where(FinePayment.fine_id == fine_id)
            )
        )

        outstanding = Decimal(fine.amount) - total_paid

        if outstanding <= 0:
            raise HTTPException(
                status_code=409,
                detail="Fine is already fully paid"
            )

        if amount > outstanding:
            raise HTTPException(
                status_code=409,
                detail="Payment exceeds outstanding fine"
            )

        payment = FinePayment(
            fine_id=fine.id,
            amount=amount
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        return payment

    except Exception:
        db.rollback()
        raise
