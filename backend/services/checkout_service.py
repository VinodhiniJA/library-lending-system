
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.book import Book
from models.book_copy import BookCopy
from models.loan import Loan
from models.library_setting import LibrarySetting
from models.reservation import Reservation
from models.user import User

from services.reservation_service import expire_holds
from services.fine_service import (
    assess_loan_fine,
    get_outstanding_fines
)


def checkout_book(
    db: Session,
    current_user: User,
    book_id: UUID,
    auto_commit: bool = True
):
    """
    Create a book loan.

    auto_commit=True:
        Standalone checkout commits its own transaction.

    auto_commit=False:
        Librarian approval controls the transaction.
        Loan creation and approval status commit together.
    """

    try:
        # =====================================
        # 1. LOAD LIBRARY SETTINGS
        # =====================================

        settings = db.get(LibrarySetting, 1)

        if settings is None:
            raise HTTPException(
                status_code=500,
                detail="Library settings are not configured"
            )

        # =====================================
        # 2. CHECK BOOK EXISTENCE
        # =====================================

        book = db.get(Book, book_id)

        if book is None:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        # =====================================
        # 3. LOCK MEMBER
        # =====================================

        db.scalar(
            select(User)
            .where(User.id == current_user.id)
            .with_for_update()
        )

        # =====================================
        # 4. GET ACTIVE MEMBER LOANS
        # =====================================

        active_member_loans = db.scalars(
            select(Loan)
            .where(
                Loan.user_id == current_user.id,
                Loan.status == "ACTIVE"
            )
            .order_by(Loan.id)
            .with_for_update()
        ).all()

        # =====================================
        # 5. PREVENT DUPLICATE ACTIVE LOANS
        # =====================================

        duplicate_loan = db.scalar(
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

        if duplicate_loan is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "You already have an active loan "
                    "for this book"
                )
            )

        # =====================================
        # 6. ASSESS OVERDUE FINES
        # =====================================

        for active_loan in active_member_loans:
            assess_loan_fine(
                db=db,
                loan=active_loan
            )

        db.flush()

        # =====================================
        # 7. CHECK OUTSTANDING FINES
        # =====================================

        outstanding_fines = get_outstanding_fines(
            db=db,
            user_id=current_user.id
        )

        fine_block_threshold = Decimal(
            settings.fine_block_threshold
        )

        if outstanding_fines > fine_block_threshold:

            # In approval mode, never commit here.
            if auto_commit:
                db.commit()

            raise HTTPException(
                status_code=403,
                detail=(
                    "Outstanding fines exceed "
                    "borrowing limit"
                )
            )

        # =====================================
        # 8. CHECK MAXIMUM ACTIVE LOAN LIMIT
        # =====================================

        active_loans = db.scalar(
            select(func.count(Loan.id))
            .where(
                Loan.user_id == current_user.id,
                Loan.status == "ACTIVE"
            )
        )

        if active_loans >= settings.max_active_loans:
            raise HTTPException(
                status_code=409,
                detail="Maximum active loan limit reached"
            )

        # =====================================
        # 9. LOCK BOOK
        # =====================================

        db.scalar(
            select(Book)
            .where(Book.id == book_id)
            .with_for_update()
        )

        # =====================================
        # 10. EXPIRE OLD RESERVATION HOLDS
        # =====================================

        expire_holds(db, book_id)

        # =====================================
        # 11. CHECK MEMBER'S HELD RESERVATION
        # =====================================

        now = datetime.now(timezone.utc)

        held_reservation = db.scalar(
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.user_id == current_user.id,
                Reservation.status == "HELD",
                Reservation.hold_expires_at > now
            )
            .with_for_update()
        )

        if held_reservation is not None:

            available_copy = db.scalar(
                select(BookCopy)
                .where(
                    BookCopy.id == held_reservation.copy_id,
                    BookCopy.status == "HELD"
                )
                .with_for_update()
            )

            if available_copy is None:
                raise HTTPException(
                    status_code=409,
                    detail="Reserved copy is unavailable"
                )

            held_reservation.status = "FULFILLED"
            held_reservation.copy_id = None
            held_reservation.hold_expires_at = None

        else:

            # =====================================
            # 12. PROTECT RESERVATION QUEUE
            # =====================================

            pending_reservation = db.scalar(
                select(Reservation.id)
                .where(
                    Reservation.book_id == book_id,
                    Reservation.status.in_(
                        ["WAITING", "HELD"]
                    )
                )
                .limit(1)
            )

            if pending_reservation is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Book has pending reservations"
                )

            # =====================================
            # 13. FIND AVAILABLE COPY
            # =====================================

            available_copy = db.scalar(
                select(BookCopy)
                .where(
                    BookCopy.book_id == book_id,
                    BookCopy.status == "AVAILABLE"
                )
                .order_by(BookCopy.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )

            if available_copy is None:
                raise HTTPException(
                    status_code=409,
                    detail="No available copies"
                )

        # =====================================
        # 14. CALCULATE LOAN DATES
        # =====================================

        now = datetime.now(timezone.utc)

        borrowed_at = now.replace(tzinfo=None)

        due_at = borrowed_at + timedelta(
            days=settings.loan_period_days
        )

        # =====================================
        # 15. CREATE LOAN
        # =====================================

        new_loan = Loan(
            user_id=current_user.id,
            copy_id=available_copy.id,
            borrowed_at=borrowed_at,
            due_at=due_at,
            status="ACTIVE"
        )

        # =====================================
        # 16. UPDATE COPY STATUS
        # =====================================

        available_copy.status = "BORROWED"

        db.add(new_loan)

        # =====================================
        # 17. FLUSH DATABASE CHANGES
        # =====================================

        db.flush()

        # =====================================
        # 18. COMMIT ONLY WHEN REQUESTED
        # =====================================

        if auto_commit:
            db.commit()
            db.refresh(new_loan)

        return new_loan

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
