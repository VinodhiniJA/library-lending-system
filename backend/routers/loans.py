
from datetime import datetime, timezone
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db

from models.user import User
from models.book import Book
from models.book_copy import BookCopy
from models.loan import Loan
from models.checkout_request import CheckoutApproval

from core.dependencies import (
    get_current_user,
    require_member,
    require_librarian
)

from schemas.loan_schema import (
    CheckoutRequest,
    LoanResponse
)

from services.checkout_service import checkout_book
from services.return_service import return_book


router = APIRouter(
    prefix="/loans",
    tags=["Loan Management"]
)


# =====================================
# HELPER: FORMAT CHECKOUT REQUEST
# =====================================

def request_details(request, db: Session):

    user = db.get(User, request.user_id)
    book = db.get(Book, request.book_id)

    return {
        "id": str(request.id),
        "user_id": str(request.user_id),
        "member_name": user.name if user else "Unknown",
        "book_id": str(request.book_id),
        "book_title": book.title if book else "Unknown",
        "status": request.status,
        "created_at": request.created_at,
        "reviewed_at": request.reviewed_at
    }


# =====================================
# MEMBER: REQUEST CHECKOUT
# =====================================

@router.post(
    "/checkout",
    status_code=status.HTTP_201_CREATED
)
def request_checkout(
    checkout_data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_member)
):

    try:
        book_id = checkout_data.book_id

        # Lock member to serialize requests.
        db.scalar(
            select(User)
            .where(User.id == current_user.id)
            .with_for_update()
        )

        book = db.get(Book, book_id)

        if book is None:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        # =====================================
        # CHECK BOOK AVAILABILITY
        # =====================================

        available_copies = db.scalar(
            select(func.count(BookCopy.id))
            .where(
                BookCopy.book_id == book_id,
                BookCopy.status == "AVAILABLE"
            )
        ) or 0

        if available_copies <= 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    "No available copies. "
                    "Please reserve this book instead."
                )
            )

        # =====================================
        # PREVENT DUPLICATE ACTIVE LOAN
        # =====================================

        existing_loan = db.scalar(
            select(Loan.id)
            .join(
                BookCopy,
                Loan.copy_id == BookCopy.id
            )
            .where(
                Loan.user_id == current_user.id,
                Loan.status == "ACTIVE",
                BookCopy.book_id == book_id
            )
            .limit(1)
        )

        if existing_loan is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "You already have an active loan "
                    "for this book"
                )
            )

        # =====================================
        # PREVENT DUPLICATE PENDING REQUEST
        # =====================================

        pending_request = db.scalar(
            select(CheckoutApproval.id)
            .where(
                CheckoutApproval.user_id == current_user.id,
                CheckoutApproval.book_id == book_id,
                CheckoutApproval.status == "PENDING"
            )
            .limit(1)
        )

        if pending_request is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "You already have a pending "
                    "checkout request for this book"
                )
            )

        # =====================================
        # CREATE PENDING REQUEST
        # =====================================

        new_request = CheckoutApproval(
            user_id=current_user.id,
            book_id=book_id,
            status="PENDING"
        )

        db.add(new_request)
        db.flush()

        result = request_details(new_request, db)

        db.commit()

        return {
            "message": (
                "Checkout request submitted "
                "for librarian approval"
            ),
            **result
        }

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="A pending checkout request already exists"
        )

    except Exception:
        db.rollback()
        raise


# =====================================
# MEMBER: VIEW OWN REQUESTS
# =====================================

@router.get("/requests/me")
def my_checkout_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_member)
):

    requests = db.scalars(
        select(CheckoutApproval)
        .where(
            CheckoutApproval.user_id == current_user.id
        )
        .order_by(
            CheckoutApproval.created_at.desc()
        )
    ).all()

    return [
        request_details(request, db)
        for request in requests
    ]


# =====================================
# MEMBER: CANCEL PENDING REQUEST
# =====================================

@router.post("/requests/{request_id}/cancel")
def cancel_checkout_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_member)
):

    try:
        # Lock request to avoid conflicts
        # with librarian approval/rejection.
        checkout_request = db.scalar(
            select(CheckoutApproval)
            .where(
                CheckoutApproval.id == request_id
            )
            .with_for_update()
        )

        if checkout_request is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout request not found"
            )

        # Member can cancel only their own request.
        if checkout_request.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "You cannot cancel "
                    "another member's request"
                )
            )

        # Only pending requests can be cancelled.
        if checkout_request.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only pending checkout requests "
                    "can be cancelled"
                )
            )

        checkout_request.status = "CANCELLED"

        checkout_request.reviewed_at = (
            datetime.now(timezone.utc)
        )

        db.commit()

        return {
            "message": "Request cancelled successfully",
            "request_id": str(checkout_request.id),
            "status": "CANCELLED"
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# LIBRARIAN: VIEW ALL REQUESTS
# =====================================

@router.get("/requests")
def list_checkout_requests(
    db: Session = Depends(get_db),
    librarian: User = Depends(require_librarian)
):

    requests = db.scalars(
        select(CheckoutApproval)
        .order_by(
            CheckoutApproval.created_at.desc()
        )
    ).all()

    return [
        request_details(request, db)
        for request in requests
    ]


# =====================================
# LIBRARIAN: APPROVE CHECKOUT
# =====================================

@router.post("/requests/{request_id}/approve")
def approve_checkout(
    request_id: UUID,
    db: Session = Depends(get_db),
    librarian: User = Depends(require_librarian)
):

    try:
        # Lock request to prevent duplicate approval.
        checkout_request = db.scalar(
            select(CheckoutApproval)
            .where(
                CheckoutApproval.id == request_id
            )
            .with_for_update()
        )

        if checkout_request is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout request not found"
            )

        if checkout_request.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail=(
                    "This checkout request "
                    "has already been reviewed"
                )
            )

        # =====================================
        # VALIDATE MEMBER ACCOUNT
        # =====================================

        member = db.get(
            User,
            checkout_request.user_id
        )

        if member is None or not member.is_active:
            raise HTTPException(
                status_code=403,
                detail="Member account is unavailable"
            )

        if member.role != "MEMBER":
            raise HTTPException(
                status_code=403,
                detail="Invalid member account"
            )

        # =====================================
        # CREATE LOAN WITHOUT COMMIT
        # =====================================

        new_loan = checkout_book(
            db=db,
            current_user=member,
            book_id=checkout_request.book_id,
            auto_commit=False
        )

        # =====================================
        # UPDATE APPROVAL STATUS
        # =====================================

        checkout_request.status = "APPROVED"

        checkout_request.reviewed_by = librarian.id

        checkout_request.reviewed_at = (
            datetime.now(timezone.utc)
        )

        db.flush()

        loan_id = str(new_loan.id)
        approved_request_id = str(checkout_request.id)

        # =====================================
        # SINGLE ATOMIC COMMIT
        # =====================================

        db.commit()

        return {
            "message": "Checkout approved successfully",
            "request_id": approved_request_id,
            "loan_id": loan_id,
            "status": "APPROVED"
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# LIBRARIAN: REJECT CHECKOUT
# =====================================

@router.post("/requests/{request_id}/reject")
def reject_checkout(
    request_id: UUID,
    db: Session = Depends(get_db),
    librarian: User = Depends(require_librarian)
):

    try:
        checkout_request = db.scalar(
            select(CheckoutApproval)
            .where(
                CheckoutApproval.id == request_id
            )
            .with_for_update()
        )

        if checkout_request is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout request not found"
            )

        if checkout_request.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail=(
                    "This checkout request "
                    "has already been reviewed"
                )
            )

        checkout_request.status = "REJECTED"

        checkout_request.reviewed_by = librarian.id

        checkout_request.reviewed_at = (
            datetime.now(timezone.utc)
        )

        db.commit()

        return {
            "message": "Checkout request rejected",
            "request_id": str(request_id),
            "status": "REJECTED"
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# RETURN BOOK
# =====================================

@router.post(
    "/{loan_id}/return",
    response_model=LoanResponse
)
def return_loan(
    loan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return return_book(
        db=db,
        current_user=current_user,
        loan_id=loan_id
    )
