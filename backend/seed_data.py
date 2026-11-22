
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, func

from database import SessionLocal
from models.book import Book
from models.book_copy import BookCopy
from models.loan import Loan
from models.user import User


BOOK_DATA = [
    ("Clean Code", "Robert C. Martin"),
    ("The Pragmatic Programmer", "Andrew Hunt"),
    ("Python Crash Course", "Eric Matthes"),
    ("Fluent Python", "Luciano Ramalho"),
    ("Automate the Boring Stuff with Python", "Al Sweigart"),
    ("Effective Python", "Brett Slatkin"),
    ("Learning Python", "Mark Lutz"),
    ("Python Cookbook", "David Beazley"),
    ("Think Python", "Allen B. Downey"),
    ("Introduction to Algorithms", "Thomas H. Cormen"),
    ("Grokking Algorithms", "Aditya Bhargava"),
    ("Data Structures and Algorithms in Python", "Michael T. Goodrich"),
    ("Algorithms", "Robert Sedgewick"),
    ("Design Patterns", "Erich Gamma"),
    ("Head First Design Patterns", "Eric Freeman"),
    ("Refactoring", "Martin Fowler"),
    ("The Clean Coder", "Robert C. Martin"),
    ("Code Complete", "Steve McConnell"),
    ("Computer Networks", "Andrew S. Tanenbaum"),
    ("Operating System Concepts", "Abraham Silberschatz"),
    ("Database System Concepts", "Abraham Silberschatz"),
    ("Fundamentals of Database Systems", "Ramez Elmasri"),
    ("SQL Performance Explained", "Markus Winand"),
    ("Learning SQL", "Alan Beaulieu"),
    ("SQL Cookbook", "Anthony Molinaro"),
    ("Designing Data-Intensive Applications", "Martin Kleppmann"),
    ("System Design Interview", "Alex Xu"),
    ("Building Microservices", "Sam Newman"),
    ("FastAPI", "Bill Lubanovic"),
    ("Django for Beginners", "William S. Vincent"),
    ("Eloquent JavaScript", "Marijn Haverbeke"),
    ("JavaScript: The Definitive Guide", "David Flanagan"),
    ("You Don't Know JS Yet", "Kyle Simpson"),
    ("Angular Up and Running", "Shyam Seshadri"),
    ("Learning React", "Alex Banks"),
    ("Hands-On Machine Learning", "Aurelien Geron"),
    ("Deep Learning", "Ian Goodfellow"),
    ("Pattern Recognition and Machine Learning", "Christopher Bishop"),
    ("Natural Language Processing with Python", "Steven Bird"),
    ("Artificial Intelligence: A Modern Approach", "Stuart Russell"),
]


def seed_books(db):
    existing_count = db.scalar(select(func.count(Book.id)))

    for title, author in BOOK_DATA:
        exists = db.scalar(
            select(Book.id).where(Book.title == title)
        )
        if exists:
            continue

        if existing_count >= 40:
            break

        book = Book(
            title=title,
            author=author,
            total_copies=2,
        )
        db.add(book)
        db.flush()

        db.add_all([
            BookCopy(book_id=book.id, status="AVAILABLE"),
            BookCopy(book_id=book.id, status="AVAILABLE"),
        ])
        existing_count += 1


def seed_members(db):
    members = [
        ("Ananya", "ananya.seed@example.com"),
        ("Rohit", "rohit.seed@example.com"),
        ("Meera", "meera.seed@example.com"),
    ]

    existing_count = db.scalar(
        select(func.count(User.id)).where(User.role == "MEMBER")
    )

    # Reuse the application's own password hashing implementation.
    from core.security import hash_password

    for name, email in members:
        if existing_count >= 10:
            break

        exists = db.scalar(
            select(User.id).where(User.email == email)
        )
        if exists:
            continue

        db.add(User(
            name=name,
            email=email,
            password_hash=hash_password("Member@123"),
            role="MEMBER",
            is_active=True,
        ))
        existing_count += 1


def seed_loans(db):
    existing_count = db.scalar(select(func.count(Loan.id)))
    missing = max(0, 25 - existing_count)

    if missing == 0:
        return

    members = db.scalars(
        select(User)
        .where(User.role == "MEMBER")
        .order_by(User.email)
    ).all()

    # Only use new books with available copies.
    copies = db.scalars(
        select(BookCopy)
        .join(Book, BookCopy.book_id == Book.id)
        .where(
            BookCopy.status == "AVAILABLE",
            Book.title != "Advanced Python Programming",
        )
        .order_by(Book.title, BookCopy.id)
    ).all()

    if not members or len(copies) < missing:
        raise RuntimeError(
            "Insufficient members or available copies for seed loans."
        )

    now = datetime.now(timezone.utc)

    for index, copy in enumerate(copies[:missing]):
        member = members[index % len(members)]

        # Seed historical returned loans so existing borrowing limits,
        # fine restrictions, and reservations remain unaffected.
        borrowed_at = now - timedelta(days=40 + index)
        due_at = borrowed_at + timedelta(days=14)
        returned_at = borrowed_at + timedelta(days=7)

        db.add(Loan(
            user_id=member.id,
            copy_id=copy.id,
            borrowed_at=borrowed_at,
            due_at=due_at,
            returned_at=returned_at,
            status="RETURNED",
        ))


def main():
    db = SessionLocal()

    try:
        seed_books(db)
        db.flush()

        seed_members(db)
        db.flush()

        seed_loans(db)
        db.commit()

        print("Seed data completed successfully!")

        print("Books:", db.scalar(select(func.count(Book.id))))
        print(
            "Members:",
            db.scalar(
                select(func.count(User.id))
                .where(User.role == "MEMBER")
            ),
        )
        print("Loans:", db.scalar(select(func.count(Loan.id))))

    except Exception as error:
        db.rollback()
        print("Seed failed:", error)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
