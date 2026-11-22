
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.password_reset import PasswordReset
from models.auth_session import AuthSession
from core.security import hash_password, settings
from services.email_service import send_verification_email

router = APIRouter(
    prefix="/auth",
    tags=["Password Reset"]
)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value):
        if not (
            any(c.isupper() for c in value)
            and any(c.islower() for c in value)
            and any(c.isdigit() for c in value)
            and any(not c.isalnum() for c in value)
        ):
            raise ValueError(
                "Password must contain uppercase, lowercase, "
                "number and special character"
            )
        return value


def otp_hash(user_id, otp):
    value = f"password-reset:{user_id}:{otp}:{settings.JWT_SECRET_KEY}"
    return hashlib.sha256(value.encode()).hexdigest()


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    message = {
        "message": "If the email is registered, a reset OTP will be sent."
    }

    user = db.scalar(
        select(User).where(User.email == str(request.email))
    )

    if not user:
        return message

    now = datetime.now(timezone.utc)

    reset = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id)
        .with_for_update()
    )

    if reset:
        last_sent = reset.last_sent_at
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)

        if (now - last_sent).total_seconds() < 60:
            return message

    otp = f"{secrets.randbelow(1000000):06d}"

    if not reset:
        reset = PasswordReset(user_id=user.id)
        db.add(reset)

    reset.otp_hash = otp_hash(user.id, otp)
    reset.expires_at = now + timedelta(minutes=10)
    reset.attempts = 0
    reset.last_sent_at = now

    try:
        send_verification_email(user.email, otp)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Unable to send password reset email"
        )

    return message


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.scalar(
        select(User)
        .where(User.email == str(request.email))
        .with_for_update()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP"
        )

    reset = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.user_id == user.id)
        .with_for_update()
    )

    if not reset:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP"
        )

    now = datetime.now(timezone.utc)

    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at or reset.attempts >= 5:
        raise HTTPException(
            status_code=400,
            detail="OTP expired or maximum attempts reached"
        )

    expected_hash = otp_hash(user.id, request.otp)

    if not secrets.compare_digest(
        reset.otp_hash,
        expected_hash
    ):
        reset.attempts += 1
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    user.password_hash = hash_password(request.new_password)

    # Invalidate existing refresh sessions after password reset.
    sessions = db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id)
    ).all()

    for session in sessions:
        session.revoked_at = now

    db.delete(reset)
    db.commit()

    return {
        "message": "Password reset successful",
        "next_step": "LOGIN"
    }
