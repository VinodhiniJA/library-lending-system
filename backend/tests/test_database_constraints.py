
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from models.book import Book
from models.book_copy import BookCopy
from models.user import User
from models.library_setting import LibrarySetting


def test_create_book(db):
    book = Book(
        title="Test Python",
        author="Test Author",
        total_copies=1
    )
    db.add(book)
    db.commit()

    assert book.id is not None


def test_book_title_cannot_be_empty(db):
    book = Book(
        title="",
        author="Test Author",
        total_copies=1
    )
    db.add(book)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_negative_total_copies_rejected(db):
    book = Book(
        title="Invalid Book",
        author="Test Author",
        total_copies=-1
    )
    db.add(book)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_create_book_copy(db):
    book = Book(
        title="Copy Test",
        author="Test Author",
        total_copies=1
    )
    db.add(book)
    db.flush()

    copy = BookCopy(
        book_id=book.id,
        status="AVAILABLE"
    )
    db.add(copy)
    db.commit()

    assert copy.id is not None
    assert copy.status == "AVAILABLE"


def test_invalid_copy_status_rejected(db):
    book = Book(
        title="Status Test",
        author="Test Author",
        total_copies=1
    )
    db.add(book)
    db.flush()

    copy = BookCopy(
        book_id=book.id,
        status="LOST"
    )
    db.add(copy)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_invalid_user_role_rejected(db):
    user = User(
        name="Invalid User",
        email=f"{uuid.uuid4()}@example.com",
        password_hash="test_hash",
        role="ADMIN"
    )
    db.add(user)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_duplicate_email_rejected(db):
    email = f"{uuid.uuid4()}@example.com"

    first = User(
        name="First User",
        email=email,
        password_hash="test_hash",
        role="MEMBER"
    )
    second = User(
        name="Second User",
        email=email,
        password_hash="test_hash",
        role="MEMBER"
    )

    db.add_all([first, second])

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_library_settings_positive_loan_period(db):
    settings = LibrarySetting(
        id=1,
        loan_period_days=0
    )
    db.add(settings)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_library_settings_negative_fine_rejected(db):
    settings = LibrarySetting(
        id=1,
        fine_per_day=Decimal("-5.00")
    )
    db.add(settings)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_library_settings_valid(db):
    settings = LibrarySetting(
        id=1,
        loan_period_days=14,
        fine_per_day=Decimal("5.00"),
        max_fine_amount=Decimal("100.00"),
        max_active_loans=3,
        hold_period_hours=24,
        fine_block_threshold=Decimal("50.00")
    )

    db.add(settings)
    db.commit()

    assert settings.loan_period_days == 14
    assert settings.hold_period_hours == 24
