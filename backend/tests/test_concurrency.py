
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker

from conftest import test_engine
from models.book import Book
from models.book_copy import BookCopy
from models.user import User
from models.loan import Loan
from models.library_setting import LibrarySetting
from services.checkout_service import checkout_book


def test_concurrent_checkout_last_copy():
    # This test uses two independent database sessions.
    # All records are created only in the dedicated test DB.

    SessionFactory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    book_id = None
    copy_id = None
    member_ids = []

    # Prepare and commit data so both threads can see it.
    with SessionFactory() as db:
        settings = LibrarySetting(
            id=1,
            loan_period_days=14,
            fine_per_day=Decimal("5.00"),
            max_fine_amount=Decimal("100.00"),
            max_active_loans=3,
            hold_period_hours=24,
            fine_block_threshold=Decimal("50.00"),
        )

        book = Book(
            title=f"Concurrency Test {uuid4()}",
            author="Test Author",
            total_copies=1,
        )

        members = [
            User(
                name=f"Concurrent Member {i}",
                email=f"concurrent_{uuid4()}@example.com",
                password_hash="test_hash",
                role="MEMBER",
            )
            for i in range(2)
        ]

        db.add_all([settings, book, *members])
        db.flush()

        copy = BookCopy(
            book_id=book.id,
            status="AVAILABLE",
        )

        db.add(copy)
        db.commit()

        book_id = book.id
        copy_id = copy.id
        member_ids = [member.id for member in members]

    barrier = Barrier(2)

    def attempt_checkout(member_id):
        with SessionFactory() as db:
            member = db.get(User, member_id)

            # Synchronize both workers immediately
            # before calling checkout_book().
            barrier.wait(timeout=10)

            try:
                loan = checkout_book(
                    db=db,
                    current_user=member,
                    book_id=book_id,
                )
                return ("SUCCESS", loan.id)

            except HTTPException as exc:
                return ("REJECTED", exc.status_code)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(attempt_checkout, member_ids)
            )

        successful = [
            result for result in results
            if result[0] == "SUCCESS"
        ]

        rejected = [
            result for result in results
            if result[0] == "REJECTED"
        ]

        assert len(successful) == 1, results
        assert len(rejected) == 1, results
        assert rejected[0][1] == 409, results

        with SessionFactory() as db:
            active_loans = db.scalar(
                select(func.count(Loan.id)).where(
                    Loan.copy_id == copy_id,
                    Loan.status == "ACTIVE",
                )
            )

            copy = db.get(BookCopy, copy_id)

            assert active_loans == 1
            assert copy.status == "BORROWED"

    finally:
        # Clean up records created by this test.
        with SessionFactory() as db:
            loans = db.scalars(
                select(Loan).where(
                    Loan.copy_id == copy_id
                )
            ).all()

            for loan in loans:
                db.delete(loan)

            db.flush()

            copy = db.get(BookCopy, copy_id)
            if copy is not None:
                db.delete(copy)

            db.flush()

            for member_id in member_ids:
                member = db.get(User, member_id)
                if member is not None:
                    db.delete(member)

            book = db.get(Book, book_id)
            if book is not None:
                db.delete(book)

            settings = db.get(LibrarySetting, 1)
            if settings is not None:
                db.delete(settings)

            db.commit()
