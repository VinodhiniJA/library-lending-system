
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db

from models.user import User
from models.loan import Loan
from models.fine import Fine

from core.dependencies import (
    get_current_user,
    require_member,
    require_librarian
)

from schemas.fine_schema import (
    FinePaymentCreate,
    FinePaymentResponse,
    FineResponse
)

from services.fine_payment_service import (
    get_member_fines,
    record_fine_payment
)


router = APIRouter(
    prefix="/fines",
    tags=["Fine Management"]
)


# =====================================
# MEMBER: VIEW FINES
# =====================================

@router.get(
    "/me",
    response_model=list[FineResponse]
)
def my_fines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_member_fines(
        db,
        current_user.id
    )


# =====================================
# MEMBER: OUTSTANDING AMOUNT
# =====================================

@router.get("/me/outstanding")
def my_outstanding_fines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fines = get_member_fines(
        db,
        current_user.id
    )

    return {
        "outstanding_amount": sum(
            (
                fine["outstanding_amount"]
                for fine in fines
            ),
            start=Decimal("0.00")
        )
    }


# =====================================
# MEMBER: DEMO FINE PAYMENT
# =====================================

@router.post("/{fine_id}/demo-pay")
def demo_pay_fine(
    fine_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_member)
):
    # Confirm that the fine belongs to this member.
    fine = db.scalar(
        select(Fine)
        .join(Loan, Fine.loan_id == Loan.id)
        .where(
            Fine.id == fine_id,
            Loan.user_id == current_user.id
        )
    )

    if fine is None:
        raise HTTPException(
            status_code=404,
            detail="Fine not found for this member"
        )

    # Calculate the current outstanding balance.
    fines = get_member_fines(db, current_user.id)

    matching_fine = next(
        (item for item in fines if item["id"] == fine_id),
        None
    )

    if matching_fine is None:
        raise HTTPException(
            status_code=404,
            detail="Fine not found"
        )

    outstanding = Decimal(
        matching_fine["outstanding_amount"]
    )

    if outstanding <= 0:
        raise HTTPException(
            status_code=409,
            detail="Fine is already fully paid"
        )

    # Existing service locks the fine and rechecks
    # the balance before recording payment.
    payment = record_fine_payment(
        db=db,
        fine_id=fine_id,
        amount=outstanding
    )

    return {
        "message": "Demo fine payment completed",
        "payment_type": "DEMO",
        "real_money_collected": False,
        "payment_id": str(payment.id),
        "fine_id": str(fine_id),
        "amount": str(payment.amount),
        "status": "PAID"
    }


# =====================================
# LIBRARIAN: RECORD PAYMENT
# =====================================

@router.post(
    "/{fine_id}/payments",
    response_model=FinePaymentResponse,
    status_code=201
)
def pay_fine(
    fine_id: UUID,
    payment_data: FinePaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    return record_fine_payment(
        db=db,
        fine_id=fine_id,
        amount=payment_data.amount
    )
