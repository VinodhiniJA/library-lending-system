
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.book import Book
from models.loan import Loan
from models.book_copy import BookCopy
from models.user import User

from services.fine_service import assess_loan_fine
from services.reservation_service import (
    allocate_waiting_reservations
)


def return_book(
    db: Session,
    current_user: User,
    loan_id: UUID
):
    try:
        # 1. Find loan
        loan = db.scalar(
            select(Loan)
            .where(Loan.id == loan_id)
        )

        if loan is None:
            raise HTTPException(
                status_code=404,
                detail="Loan not found"
            )

        # 2. Verify permission
        if (
            current_user.role != "LIBRARIAN"
            and loan.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You cannot return another member's book"
            )

        # 3. Lock book first to coordinate
        # with reservation queue operations
        book_copy = db.get(BookCopy, loan.copy_id)

        if book_copy is None:
            raise HTTPException(
                status_code=404,
                detail="Book copy not found"
            )

        db.scalar(
            select(Book)
            .where(Book.id == book_copy.book_id)
            .with_for_update()
        )

        # 4. Lock and refresh loan
        loan = db.scalar(
            select(Loan)
            .where(Loan.id == loan_id)
            .with_for_update()
        )

        if loan.status != "ACTIVE":
            raise HTTPException(
                status_code=409,
                detail="Book has already been returned"
            )

        # 5. Lock physical copy
        book_copy = db.scalar(
            select(BookCopy)
            .where(BookCopy.id == loan.copy_id)
            .with_for_update()
        )

        # 6. Record return time
        now = datetime.now(timezone.utc)

        # Loan model currently uses naive UTC timestamps
        returned_at = now.replace(tzinfo=None)

        loan.status = "RETURNED"
        loan.returned_at = returned_at

        # 7. Assess overdue fine
        assess_loan_fine(
            db=db,
            loan=loan,
            now=returned_at
        )

        # 8. Release physical copy
        book_copy.status = "AVAILABLE"
        db.flush()

        # 9. Allocate returned copy to waiting
        # members in FIFO order
        allocate_waiting_reservations(
            db=db,
            book_id=book_copy.book_id,
            now=now
        )

        # 10. Commit loan, fine, and reservation
        db.commit()
        db.refresh(loan)

        return loan

    except Exception:
        db.rollback()
        raise
