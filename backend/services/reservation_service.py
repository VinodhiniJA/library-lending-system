
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.book import Book
from models.book_copy import BookCopy
from models.loan import Loan
from models.reservation import Reservation
from models.library_setting import LibrarySetting
from models.user import User


def utc_now():
    return datetime.now(timezone.utc)


def allocate_waiting_reservations(
    db: Session,
    book_id: UUID,
    now: datetime | None = None
):
    """Assign available copies in FIFO order."""

    now = now or utc_now()

    settings = db.get(LibrarySetting, 1)

    if settings is None:
        raise HTTPException(
            status_code=500,
            detail="Library settings are not configured"
        )

    allocated = []

    while True:
        reservation = db.scalar(
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status == "WAITING"
            )
            .order_by(
                Reservation.created_at,
                Reservation.id
            )
            .with_for_update()
            .limit(1)
        )

        if reservation is None:
            break

        copy = db.scalar(
            select(BookCopy)
            .where(
                BookCopy.book_id == book_id,
                BookCopy.status == "AVAILABLE"
            )
            .order_by(BookCopy.id)
            .with_for_update()
            .limit(1)
        )

        if copy is None:
            break

        reservation.status = "HELD"
        reservation.copy_id = copy.id
        reservation.hold_expires_at = (
            now + timedelta(
                hours=settings.hold_period_hours
            )
        )

        copy.status = "HELD"

        db.flush()
        allocated.append(reservation)

    return allocated


def expire_holds(
    db: Session,
    book_id: UUID,
    now: datetime | None = None
):
    """Expire old holds and reassign copies."""

    now = now or utc_now()

    expired_holds = db.scalars(
        select(Reservation)
        .where(
            Reservation.book_id == book_id,
            Reservation.status == "HELD",
            Reservation.hold_expires_at <= now
        )
        .order_by(
            Reservation.hold_expires_at,
            Reservation.id
        )
        .with_for_update()
    ).all()

    for reservation in expired_holds:
        copy = db.scalar(
            select(BookCopy)
            .where(
                BookCopy.id == reservation.copy_id
            )
            .with_for_update()
        )

        reservation.status = "EXPIRED"
        reservation.copy_id = None
        reservation.hold_expires_at = None

        if copy is not None:
            copy.status = "AVAILABLE"

    db.flush()

    allocate_waiting_reservations(
        db=db,
        book_id=book_id,
        now=now
    )

    return len(expired_holds)


def create_reservation(
    db: Session,
    current_user: User,
    book_id: UUID
):
    try:
        # 1. Lock the book
        book = db.scalar(
            select(Book)
            .where(Book.id == book_id)
            .with_for_update()
        )

        if book is None:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        # 2. Refresh expired holds
        expire_holds(db, book_id)

        # 3. Prevent duplicate reservations
        existing = db.scalar(
            select(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.user_id == current_user.id,
                Reservation.status.in_(
                    ["WAITING", "HELD"]
                )
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="You already have an active reservation"
            )

        # 4. Prevent reserving an already borrowed book
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
                detail="You already borrowed this book"
            )

        # 5. Check available copies
        available_copy = db.scalar(
            select(BookCopy.id)
            .where(
                BookCopy.book_id == book_id,
                BookCopy.status == "AVAILABLE"
            )
            .limit(1)
        )

        # 6. Check existing waiting queue
        waiting_reservation = db.scalar(
            select(Reservation.id)
            .where(
                Reservation.book_id == book_id,
                Reservation.status == "WAITING"
            )
            .limit(1)
        )

        # 7. Reject if book is freely available
        if (
            available_copy is not None
            and waiting_reservation is None
        ):
            raise HTTPException(
                status_code=409,
                detail="Book is available; checkout instead"
            )

        # 8. Create reservation
        reservation = Reservation(
            user_id=current_user.id,
            book_id=book_id,
            status="WAITING"
        )

        db.add(reservation)
        db.commit()
        db.refresh(reservation)

        return reservation

    except Exception:
        db.rollback()
        raise


def cancel_reservation(
    db: Session,
    current_user: User,
    reservation_id: UUID
):
    try:
        # 1. Find reservation
        reservation = db.scalar(
            select(Reservation)
            .where(Reservation.id == reservation_id)
        )

        if reservation is None:
            raise HTTPException(
                status_code=404,
                detail="Reservation not found"
            )

        # 2. Verify permissions
        if (
            reservation.user_id != current_user.id
            and current_user.role != "LIBRARIAN"
        ):
            raise HTTPException(
                status_code=403,
                detail="Not allowed to cancel this reservation"
            )

        # 3. Lock book to coordinate queue operations
        db.scalar(
            select(Book)
            .where(Book.id == reservation.book_id)
            .with_for_update()
        )

        # 4. Lock and refresh reservation
        reservation = db.scalar(
            select(Reservation)
            .where(Reservation.id == reservation_id)
            .with_for_update()
        )

        if reservation.status not in ["WAITING", "HELD"]:
            raise HTTPException(
                status_code=409,
                detail="Reservation cannot be cancelled"
            )

        # 5. Release held copy if necessary
        if reservation.status == "HELD":
            copy = db.scalar(
                select(BookCopy)
                .where(
                    BookCopy.id == reservation.copy_id
                )
                .with_for_update()
            )

            if copy is not None:
                copy.status = "AVAILABLE"

        book_id = reservation.book_id

        # 6. Cancel reservation
        reservation.status = "CANCELLED"
        reservation.copy_id = None
        reservation.hold_expires_at = None

        db.flush()

        # 7. Reassign released copy to next member
        allocate_waiting_reservations(
            db=db,
            book_id=book_id
        )

        db.commit()
        db.refresh(reservation)

        return reservation

    except Exception:
        db.rollback()
        raise
