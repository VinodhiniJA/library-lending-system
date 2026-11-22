
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from core.dependencies import require_member
from models.user import User
from models.loan import Loan
from models.book_copy import BookCopy
from models.book import Book
from models.reservation import Reservation
from services.fine_service import get_outstanding_fines

router = APIRouter(
    prefix="/dashboard",
    tags=["Member Dashboard"]
)


@router.get("/me")
def member_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_member)
):
    loans = db.execute(
        select(Loan, Book.title)
        .join(BookCopy, Loan.copy_id == BookCopy.id)
        .join(Book, BookCopy.book_id == Book.id)
        .where(Loan.user_id == current_user.id)
        .order_by(Loan.borrowed_at.desc())
    ).all()

    reservations = db.execute(
        select(Reservation, Book.title)
        .join(Book, Reservation.book_id == Book.id)
        .where(Reservation.user_id == current_user.id)
        .order_by(Reservation.created_at.desc())
    ).all()

    active_loans = [
        {
            "loan_id": str(loan.id),
            "book_title": title,
            "borrowed_at": loan.borrowed_at,
            "due_at": loan.due_at,
            "status": loan.status
        }
        for loan, title in loans
        if loan.status == "ACTIVE"
    ]

    loan_history = [
        {
            "loan_id": str(loan.id),
            "book_title": title,
            "borrowed_at": loan.borrowed_at,
            "due_at": loan.due_at,
            "returned_at": loan.returned_at,
            "status": loan.status
        }
        for loan, title in loans
    ]

    reservation_details = [
        {
            "reservation_id": str(reservation.id),
            "book_title": title,
            "status": reservation.status,
            "created_at": reservation.created_at,
            "hold_expires_at": reservation.hold_expires_at
        }
        for reservation, title in reservations
    ]

    outstanding_fines = get_outstanding_fines(
        db=db,
        user_id=current_user.id
    )

    return {
        "member": {
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email
        },
        "summary": {
            "active_loans": len(active_loans),
            "total_loans": len(loan_history),
            "active_reservations": sum(
                r["status"] in ("WAITING", "HELD")
                for r in reservation_details
            ),
            "outstanding_fines": float(outstanding_fines)
        },
        "active_loans": active_loans,
        "loan_history": loan_history,
        "reservations": reservation_details
    }
