
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from models.book import Book
from models.book_copy import BookCopy
from models.user import User
from models.loan import Loan
from models.reservation import Reservation
from models.library_setting import LibrarySetting

from services.checkout_service import checkout_book
from services.return_service import return_book
from services.fine_service import calculate_fine
from services.reservation_service import (
    allocate_waiting_reservations,
    expire_holds,
)


@pytest.fixture
def library(db):
    settings = LibrarySetting(
        id=1,
        loan_period_days=14,
        fine_per_day=Decimal("5.00"),
        max_fine_amount=Decimal("100.00"),
        max_active_loans=3,
        hold_period_hours=24,
        fine_block_threshold=Decimal("50.00"),
    )

    members = [
        User(
            name=f"Member {i}",
            email=f"{uuid4()}@example.com",
            password_hash="test_hash",
            role="MEMBER",
        )
        for i in range(5)
    ]

    book = Book(
        title="Business Logic Test Book",
        author="Test Author",
        total_copies=4,
    )

    db.add_all([settings, book, *members])
    db.flush()

    copies = [
        BookCopy(book_id=book.id, status="AVAILABLE")
        for _ in range(4)
    ]

    db.add_all(copies)
    db.flush()

    return {
        "book": book,
        "members": members,
        "copies": copies,
        "settings": settings,
    }


def create_active_loan(db, member, copy):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    copy.status = "BORROWED"

    loan = Loan(
        user_id=member.id,
        copy_id=copy.id,
        borrowed_at=now,
        due_at=now + timedelta(days=14),
        status="ACTIVE",
    )

    db.add(loan)
    db.flush()
    return loan


# --------------------------------------------------
# FINE CALCULATION TESTS
# --------------------------------------------------

FIXED_DUE = datetime(2026, 11, 1, 12, 0, 0)


def fine(returned_at):
    return calculate_fine(
        due_at=FIXED_DUE,
        returned_at=returned_at,
        fine_per_day=Decimal("5.00"),
        max_fine_amount=Decimal("100.00"),
        now=datetime(2026, 12, 1, tzinfo=timezone.utc),
    )


def test_fine_returned_early():
    assert fine(FIXED_DUE - timedelta(days=1)) == Decimal("0.00")


def test_fine_returned_exactly_on_time():
    assert fine(FIXED_DUE) == Decimal("0.00")


def test_fine_one_hour_overdue():
    assert fine(FIXED_DUE + timedelta(hours=1)) == Decimal("5.00")


def test_fine_four_days_overdue():
    assert fine(FIXED_DUE + timedelta(days=4)) == Decimal("20.00")


def test_fine_maximum_cap():
    assert fine(FIXED_DUE + timedelta(days=30)) == Decimal("100.00")


# --------------------------------------------------
# CHECKOUT TESTS
# --------------------------------------------------

def test_successful_checkout(db, library):
    book = library["book"]
    member = library["members"][0]

    loan = checkout_book(db, member, book.id)

    assert loan.status == "ACTIVE"
    assert loan.user_id == member.id

    copy = db.get(BookCopy, loan.copy_id)
    assert copy.status == "BORROWED"


def test_checkout_maximum_loan_limit(db, library):
    member = library["members"][0]

    for copy in library["copies"][:3]:
        create_active_loan(db, member, copy)

    with pytest.raises(HTTPException) as error:
        checkout_book(db, member, library["book"].id)

    assert error.value.status_code == 409


def test_checkout_no_available_copies(db, library):
    for copy in library["copies"]:
        copy.status = "BORROWED"

    db.flush()

    with pytest.raises(HTTPException) as error:
        checkout_book(
            db,
            library["members"][0],
            library["book"].id,
        )

    assert error.value.status_code == 409


# --------------------------------------------------
# RETURN TESTS
# --------------------------------------------------

def test_successful_return(db, library):
    member = library["members"][0]
    copy = library["copies"][0]

    loan = create_active_loan(db, member, copy)

    result = return_book(db, member, loan.id)

    assert result.status == "RETURNED"
    assert result.returned_at is not None

    db.refresh(copy)
    assert copy.status == "AVAILABLE"


def test_duplicate_return_rejected(db, library):
    member = library["members"][0]
    copy = library["copies"][0]

    loan = create_active_loan(db, member, copy)

    return_book(db, member, loan.id)

    with pytest.raises(HTTPException) as error:
        return_book(db, member, loan.id)

    assert error.value.status_code == 409


# --------------------------------------------------
# RESERVATION TESTS
# --------------------------------------------------

def test_fifo_reservation_allocation(db, library):
    book = library["book"]
    members = library["members"]
    copies = library["copies"]

    for copy in copies:
        copy.status = "BORROWED"

    now = datetime.now(timezone.utc)

    first = Reservation(
        user_id=members[0].id,
        book_id=book.id,
        status="WAITING",
        created_at=now - timedelta(hours=2),
    )

    second = Reservation(
        user_id=members[1].id,
        book_id=book.id,
        status="WAITING",
        created_at=now - timedelta(hours=1),
    )

    db.add_all([first, second])
    db.flush()

    copies[0].status = "AVAILABLE"
    db.flush()

    allocated = allocate_waiting_reservations(
        db, book.id, now=now
    )

    assert len(allocated) == 1
    assert first.status == "HELD"
    assert second.status == "WAITING"
    assert copies[0].status == "HELD"


def test_expired_hold_reassigned(db, library):
    book = library["book"]
    members = library["members"]
    copies = library["copies"]

    now = datetime.now(timezone.utc)

    for copy in copies:
        copy.status = "BORROWED"

    copies[0].status = "HELD"

    expired = Reservation(
        user_id=members[0].id,
        book_id=book.id,
        copy_id=copies[0].id,
        status="HELD",
        created_at=now - timedelta(days=2),
        hold_expires_at=now - timedelta(hours=1),
    )

    waiting = Reservation(
        user_id=members[1].id,
        book_id=book.id,
        status="WAITING",
        created_at=now - timedelta(hours=2),
    )

    db.add_all([expired, waiting])
    db.flush()

    count = expire_holds(
        db, book.id, now=now
    )

    assert count == 1
    assert expired.status == "EXPIRED"
    assert expired.copy_id is None
    assert waiting.status == "HELD"
    assert waiting.copy_id == copies[0].id
    assert copies[0].status == "HELD"
