
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models.user import User
from models.email_verification import EmailVerification
from models.registration_payment import RegistrationPayment

# Change this import path only if your existing
# email service is in a different folder.
from services.email_service import send_payment_receipt_email


router = APIRouter(
    prefix="/registration-payment",
    tags=["Registration Payment"]
)

REGISTRATION_FEE = Decimal("100.00")


class DemoPaymentRequest(BaseModel):
    email: EmailStr
    payment_method: Literal["UPI", "CARD", "NET_BANKING"]


@router.post("/demo-pay")
def demo_registration_payment(
    request: DemoPaymentRequest,
    db: Session = Depends(get_db)
):

    email = str(request.email).strip().lower()

    user = db.scalar(
        select(User)
        .where(User.email == email)
        .with_for_update()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Registered user not found"
        )

    verification = db.scalar(
        select(EmailVerification).where(
            EmailVerification.user_id == user.id
        )
    )

    if not verification or not verification.verified_at:
        raise HTTPException(
            status_code=400,
            detail="Please verify your email OTP before payment"
        )

    existing_payment = db.scalar(
        select(RegistrationPayment).where(
            RegistrationPayment.user_id == user.id
        )
    )

    if existing_payment:
        raise HTTPException(
            status_code=400,
            detail="Registration payment already completed"
        )

    payment = RegistrationPayment(
        user_id=user.id,
        amount=REGISTRATION_FEE,
        status="PAID",
        payment_method=request.payment_method,
        paid_at=datetime.now(timezone.utc)
    )

    db.add(payment)

    user.is_active = True

    db.commit()
    db.refresh(payment)

    # Stable member ID derived from existing user UUID.
    member_id = f"LIB-{str(user.id).upper()}"

    payment_id = str(payment.id)

    receipt_number = (
        f"REC-{payment_id[:8].upper()}"
    )

    email_sent = False

    try:

        send_payment_receipt_email(
            recipient=user.email,
            member_name=user.name,
            member_id=member_id,
            payment_id=payment_id,
            payment_method=payment.payment_method,
            amount=payment.amount,
            paid_at=payment.paid_at
        )

        email_sent = True

    except Exception as error:

        # Payment was already committed.
        # Email failure must not undo account activation.
        print(
            "Payment successful, but receipt email failed:",
            type(error).__name__,
            str(error)
        )

    return {
        "message": "Demo registration payment successful",
        "member_id": member_id,
        "receipt_number": receipt_number,
        "payment_id": payment_id,
        "amount": float(payment.amount),
        "currency": "INR",
        "payment_method": payment.payment_method,
        "payment_status": payment.status,
        "account_activated": True,
        "receipt_email_sent": email_sent,
        "real_money_collected": False,
        "next_step": "LOGIN"
    }
