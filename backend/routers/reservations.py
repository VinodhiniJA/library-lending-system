
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from core.dependencies import (
    get_current_user,
    require_member,
    require_librarian
)

from models.user import User
from models.reservation import Reservation
from models.book import Book

from schemas.reservation_schema import (
    ReservationCreate,
    ReservationResponse
)

from services.reservation_service import (
    create_reservation,
    cancel_reservation,
    expire_holds
)


router = APIRouter(
    prefix="/reservations",
    tags=["Reservation Management"]
)


# =====================================
# MEMBER: CREATE RESERVATION
# =====================================

@router.post(
    "",
    response_model=ReservationResponse,
    status_code=201
)
def reserve_book(
    data: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_member)
):
    return create_reservation(
        db=db,
        current_user=current_user,
        book_id=data.book_id
    )


# =====================================
# LIBRARIAN: VIEW ALL RESERVATIONS
# =====================================

@router.get("/librarian/all")
def librarian_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    rows = db.execute(
        select(Reservation, User, Book)
        .join(
            User,
            Reservation.user_id == User.id
        )
        .join(
            Book,
            Reservation.book_id == Book.id
        )
        .order_by(
            Reservation.created_at.desc(),
            Reservation.id.desc()
        )
    ).all()

    # Calculate FIFO queue positions for WAITING
    # reservations separately for each book.
    waiting_by_book = {}

    for reservation, user, book in rows:
        if reservation.status == "WAITING":
            book_id = reservation.book_id

            waiting_by_book.setdefault(
                book_id,
                []
            ).append(reservation)

    queue_positions = {}

    for book_id, waiting_reservations in waiting_by_book.items():
        waiting_reservations.sort(
            key=lambda reservation: (
                reservation.created_at,
                str(reservation.id)
            )
        )

        for position, reservation in enumerate(
            waiting_reservations,
            start=1
        ):
            queue_positions[reservation.id] = position

    results = []

    for reservation, user, book in rows:
        results.append({
            "id": str(reservation.id),
            "member_name": user.name,
            "member_email": user.email,
            "book_title": book.title,
            "status": reservation.status,
            "queue_position": queue_positions.get(
                reservation.id
            ),
            "created_at": reservation.created_at,
            "hold_expires_at": reservation.hold_expires_at
        })

    return results


# =====================================
# MEMBER: MY RESERVATIONS
# =====================================

@router.get(
    "/me",
    response_model=list[ReservationResponse]
)
def my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.scalars(
        select(Reservation)
        .where(
            Reservation.user_id == current_user.id
        )
        .order_by(
            Reservation.created_at.desc(),
            Reservation.id.desc()
        )
    ).all()


# =====================================
# MEMBER: CANCEL RESERVATION
# =====================================

@router.delete(
    "/{reservation_id}",
    response_model=ReservationResponse
)
def cancel_my_reservation(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return cancel_reservation(
        db=db,
        current_user=current_user,
        reservation_id=reservation_id
    )


# =====================================
# LIBRARIAN: EXPIRE RESERVATION HOLDS
# =====================================

@router.post("/expire-holds")
def expire_reservation_holds(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    try:
        books = db.scalars(
            select(Book).order_by(Book.id)
        ).all()

        expired_count = 0

        for book in books:
            db.scalar(
                select(Book)
                .where(Book.id == book.id)
                .with_for_update()
            )

            expired_count += expire_holds(
                db=db,
                book_id=book.id
            )

        db.commit()

        return {
            "expired_holds": expired_count,
            "message": "Expired holds processed successfully"
        }

    except Exception:
        db.rollback()
        raise


# =====================================
# MEMBER: RESERVATION QUEUE POSITION
# =====================================

@router.get("/{reservation_id}/position")
def reservation_queue_position(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_member)
):
    reservation = db.scalar(
        select(Reservation)
        .where(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id
        )
    )

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Reservation not found"
        )

    if reservation.status != "WAITING":
        return {
            "reservation_id": str(reservation.id),
            "status": reservation.status,
            "queue_position": None,
            "message": (
                "Reservation is not currently "
                "in the waiting queue"
            )
        }

    waiting_reservations = db.scalars(
        select(Reservation)
        .where(
            Reservation.book_id == reservation.book_id,
            Reservation.status == "WAITING"
        )
        .order_by(
            Reservation.created_at.asc(),
            Reservation.id.asc()
        )
    ).all()

    position = next(
        (
            index
            for index, item in enumerate(
                waiting_reservations,
                start=1
            )
            if item.id == reservation.id
        ),
        None
    )

    return {
        "reservation_id": str(reservation.id),
        "status": reservation.status,
        "queue_position": position,
        "members_ahead": (
            position - 1
            if position is not None
            else None
        ),
        "message": (
            f"You are number {position} "
            "in the reservation waiting list"
        )
    }
