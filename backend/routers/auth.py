
import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db

from models.user import User
from models.auth_session import AuthSession
from models.email_verification import EmailVerification

from schemas.user_schema import (
    UserRegister,
    UserResponse,
    UserLogin,
    TokenResponse,
    VerifyEmail,
    ResendOTP
)

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    settings
)

from core.dependencies import (
    get_current_user,
    require_member,
    require_librarian
)

from services.email_service import send_verification_email


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

REFRESH_COOKIE_NAME = "library_refresh"
REFRESH_COOKIE_PATH = "/auth"


# =====================================
# REFRESH COOKIE HELPERS
# =====================================

def set_refresh_cookie(
    response: Response,
    refresh_token: str
):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=False,  # Set True with HTTPS
        samesite="lax",
        path=REFRESH_COOKIE_PATH
    )


def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="lax",
        secure=False
    )


# =====================================
# EMAIL OTP HELPERS
# =====================================

def otp_digest(user_id, otp: str) -> str:
    raw = (
        f"{user_id}:{otp}:{settings.JWT_SECRET_KEY}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def issue_otp(
    db: Session,
    user: User
):
    now = datetime.now(timezone.utc)

    record = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.user_id == user.id)
        .with_for_update()
    )

    if record is not None:
        if record.verified_at is not None:
            raise HTTPException(
                status_code=409,
                detail="Email is already verified"
            )

        last_sent = record.last_sent_at

        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(
                tzinfo=timezone.utc
            )

        if (now - last_sent).total_seconds() < 60:
            raise HTTPException(
                status_code=429,
                detail="Wait 60 seconds before requesting another OTP"
            )

    otp = f"{secrets.randbelow(1000000):06d}"

    if record is None:
        record = EmailVerification(
            user_id=user.id
        )
        db.add(record)

    record.otp_hash = otp_digest(user.id, otp)
    record.expires_at = now + timedelta(minutes=10)
    record.attempts = 0
    record.verified_at = None
    record.last_sent_at = now

    db.flush()

    try:
        send_verification_email(
            user.email,
            otp
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Unable to send verification email. Please try again."
        )


# =====================================
# 1. MEMBER REGISTRATION
# =====================================

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    email = str(user_data.email).strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered"
        )

    try:
        new_user = User(
            name=user_data.name,
            email=email,
            password_hash=hash_password(
                user_data.password
            ),
            role="MEMBER",
            is_active=False
        )

        db.add(new_user)
        db.flush()

        issue_otp(
            db=db,
            user=new_user
        )

        db.commit()

        return {
            "message": (
                "Registration successful. "
                "Check your email for the verification OTP."
            ),
            "email": email,
            "verification_required": True
        }

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Email is already registered"
        )

    except Exception:
        db.rollback()
        raise


# =====================================
# 2. VERIFY EMAIL OTP
# =====================================

@router.post("/verify-email")
def verify_email(
    data: VerifyEmail,
    db: Session = Depends(get_db)
):
    email = str(data.email).strip().lower()

    try:
        user = db.scalar(
            select(User)
            .where(User.email == email)
            .with_for_update()
        )

        if user is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification code"
            )

        record = db.scalar(
            select(EmailVerification)
            .where(EmailVerification.user_id == user.id)
            .with_for_update()
        )

        if record is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification code"
            )

        if record.verified_at is not None:
            return {
                "message": "Email is already verified",
                "email_verified": True,
                "membership_active": user.is_active
            }

        now = datetime.now(timezone.utc)

        expires_at = record.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if expires_at <= now:
            raise HTTPException(
                status_code=400,
                detail="OTP has expired. Request a new OTP."
            )

        if record.attempts >= 5:
            raise HTTPException(
                status_code=429,
                detail="Maximum OTP attempts reached. Request a new OTP."
            )

        record.attempts += 1

        valid_otp = secrets.compare_digest(
            record.otp_hash,
            otp_digest(user.id, data.otp)
        )

        if not valid_otp:
            # Persist failed-attempt count before raising.
            db.commit()

            raise HTTPException(
                status_code=400,
                detail="Invalid verification code"
            )

        record.verified_at = now
        record.otp_hash = ""

        # Do not activate yet.
        # Phase 2 handles demo registration payment.
        db.commit()

        return {
            "message": (
                "Email verified successfully. "
                "Complete the demo registration payment "
                "to activate your membership."
            ),
            "email_verified": True,
            "membership_active": False,
            "next_step": "DEMO_REGISTRATION_PAYMENT"
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# 3. RESEND EMAIL OTP
# =====================================

@router.post("/resend-otp")
def resend_otp(
    data: ResendOTP,
    db: Session = Depends(get_db)
):
    email = str(data.email).strip().lower()

    try:
        user = db.scalar(
            select(User)
            .where(User.email == email)
        )

        if user is not None and not user.is_active:
            record = db.scalar(
                select(EmailVerification)
                .where(EmailVerification.user_id == user.id)
            )

            if (
                record is not None
                and record.verified_at is None
            ):
                issue_otp(
                    db=db,
                    user=user
                )

                db.commit()

        return {
            "message": (
                "If email verification is pending, "
                "a verification code has been sent."
            )
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# 4. MEMBER / LIBRARIAN LOGIN
# =====================================

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK
)
def login_user(
    login_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    email = str(login_data.email).strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if not user or not verify_password(
        login_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail=(
                "Membership is not active. "
                "Complete email verification and "
                "demo registration payment."
            )
        )

    now = datetime.now(timezone.utc)

    refresh_token = generate_refresh_token()

    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_refresh_token(
            refresh_token
        ),
        expires_at=now + timedelta(
            hours=settings.REFRESH_SESSION_EXPIRE_HOURS
        )
    )

    db.add(auth_session)
    db.commit()

    set_refresh_cookie(
        response,
        refresh_token
    )

    return TokenResponse(
        access_token=create_access_token(
            str(user.id)
        ),
        token_type="bearer"
    )


# =====================================
# 5. REFRESH ACCESS TOKEN
# =====================================

@router.post(
    "/refresh",
    response_model=TokenResponse
)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    raw_token = request.cookies.get(
        REFRESH_COOKIE_NAME
    )

    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Session not found"
        )

    now = datetime.now(timezone.utc)

    auth_session = db.scalar(
        select(AuthSession)
        .where(
            AuthSession.token_hash ==
            hash_refresh_token(raw_token)
        )
        .with_for_update()
    )

    if (
        auth_session is None
        or auth_session.revoked_at is not None
    ):
        raise HTTPException(
            status_code=401,
            detail="Session invalid"
        )

    expires_at = auth_session.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= now:
        raise HTTPException(
            status_code=401,
            detail="Session expired"
        )

    user = db.get(
        User,
        auth_session.user_id
    )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Account unavailable"
        )

    new_refresh_token = generate_refresh_token()

    auth_session.token_hash = hash_refresh_token(
        new_refresh_token
    )

    db.commit()

    set_refresh_cookie(
        response,
        new_refresh_token
    )

    return TokenResponse(
        access_token=create_access_token(
            str(user.id)
        ),
        token_type="bearer"
    )


# =====================================
# 6. LOGOUT
# =====================================

@router.post("/logout")
def logout_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    raw_token = request.cookies.get(
        REFRESH_COOKIE_NAME
    )

    if raw_token:
        auth_session = db.scalar(
            select(AuthSession)
            .where(
                AuthSession.token_hash ==
                hash_refresh_token(raw_token)
            )
            .with_for_update()
        )

        if (
            auth_session is not None
            and auth_session.revoked_at is None
        ):
            auth_session.revoked_at = (
                datetime.now(timezone.utc)
            )

            db.commit()

    clear_refresh_cookie(response)

    return {
        "message": "Logged out successfully"
    }


# =====================================
# 7. CURRENT USER PROFILE
# =====================================

@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user: User = Depends(
        get_current_user
    )
):
    return current_user


# =====================================
# 8. MEMBER-ONLY ENDPOINT
# =====================================

@router.get("/member-only")
def member_only(
    current_user: User = Depends(
        require_member
    )
):
    return {
        "message": "Welcome, Member!",
        "name": current_user.name,
        "role": current_user.role
    }


# =====================================
# 9. LIBRARIAN-ONLY ENDPOINT
# =====================================

@router.get("/librarian-only")
def librarian_only(
    current_user: User = Depends(
        require_librarian
    )
):
    return {
        "message": "Welcome, Librarian!",
        "name": current_user.name,
        "role": current_user.role
    }
