
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func

from database import SessionLocal
from models.book import Book
from models.book_copy import BookCopy
from models.loan import Loan
from models.user import User
from core.security import hash_password


# --------------------------------------------------
# 1. BOOK SEED DATA
# --------------------------------------------------

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


# --------------------------------------------------
# 2. MEMBER SEED DATA
# --------------------------------------------------

MEMBER_DATA = [
    ("Ananya", "ananya.seed@example.com"),
    ("Rohit", "rohit.seed@example.com"),
    ("Meera", "meera.seed@example.com"),
    ("Arjun", "arjun.seed@example.com"),
    ("Priya", "priya.seed@example.com"),
    ("Karthik", "karthik.seed@example.com"),
    ("Divya", "divya.seed@example.com"),
    ("Rahul", "rahul.seed@example.com"),
    ("Sneha", "sneha.seed@example.com"),
    ("Vikram", "vikram.seed@example.com"),
]


# --------------------------------------------------
# 3. SEED BOOKS
# --------------------------------------------------

def seed_books(db):

    existing_count = db.scalar(
        select(func.count(Book.id))
    )

    added = 0

    for title, author in BOOK_DATA:

        if existing_count >= 40:
            break

        exists = db.scalar(
            select(Book.id).where(Book.title == title)
        )

        if exists is not None:
            continue

        book = Book(
            title=title,
            author=author,
            total_copies=2,
        )

        db.add(book)
        db.flush()

        db.add_all([
            BookCopy(
                book_id=book.id,
                status="AVAILABLE",
            ),
            BookCopy(
                book_id=book.id,
                status="AVAILABLE",
            ),
        ])

        existing_count += 1
        added += 1

    print(f"New books added: {added}")


# --------------------------------------------------
# 4. SEED MEMBERS
# --------------------------------------------------

def seed_members(db):

    existing_count = db.scalar(
        select(func.count(User.id)).where(
            User.role == "MEMBER"
        )
    )

    added = 0

    for name, email in MEMBER_DATA:

        if existing_count >= 10:
            break

        exists = db.scalar(
            select(User.id).where(User.email == email)
        )

        if exists is not None:
            continue

        member = User(
            name=name,
            email=email,
            password_hash=hash_password("Member@123"),
            role="MEMBER",
            is_active=True,
        )

        db.add(member)

        existing_count += 1
        added += 1

    print(f"New members added: {added}")


# --------------------------------------------------
# 5. SEED LOANS
# --------------------------------------------------

def seed_loans(db):

    existing_count = db.scalar(
        select(func.count(Loan.id))
    )

    missing = max(0, 25 - existing_count)

    if missing == 0:
        print("Loan target already reached.")
        return

    members = db.scalars(
        select(User)
        .where(User.role == "MEMBER")
        .order_by(User.email)
    ).all()

    copies = db.scalars(
        select(BookCopy)
        .join(Book, BookCopy.book_id == Book.id)
        .where(
            BookCopy.status == "AVAILABLE",
            Book.title != "Advanced Python Programming",
        )
        .order_by(Book.title, BookCopy.id)
    ).all()

    if not members:
        raise RuntimeError(
            "No members available for seeding loans."
        )

    if len(copies) < missing:
        raise RuntimeError(
            "Insufficient available book copies."
        )

    now = datetime.now(timezone.utc)

    added = 0

    for index, copy in enumerate(copies[:missing]):

        member = members[index % len(members)]

        borrowed_at = now - timedelta(
            days=40 + index
        )

        due_at = borrowed_at + timedelta(days=14)

        # First five newly seeded loans are
        # historical late returns.
        if index < 5:
            returned_at = due_at + timedelta(days=3)

        # Remaining loans were returned early.
        else:
            returned_at = borrowed_at + timedelta(days=7)

        loan = Loan(
            user_id=member.id,
            copy_id=copy.id,
            borrowed_at=borrowed_at,
            due_at=due_at,
            returned_at=returned_at,
            status="RETURNED",
        )

        db.add(loan)
        added += 1

    print(f"New loans added: {added}")


# --------------------------------------------------
# 6. VERIFY SEED DATA
# --------------------------------------------------

def verify_seed_data(db):

    book_count = db.scalar(
        select(func.count(Book.id))
    )

    member_count = db.scalar(
        select(func.count(User.id)).where(
            User.role == "MEMBER"
        )
    )

    loan_count = db.scalar(
        select(func.count(Loan.id))
    )

    historical_late_returns = db.scalar(
        select(func.count(Loan.id)).where(
            Loan.returned_at.is_not(None),
            Loan.returned_at > Loan.due_at,
        )
    )

    active_overdue_loans = db.scalar(
        select(func.count(Loan.id)).where(
            Loan.status == "ACTIVE",
            Loan.due_at < datetime.now(timezone.utc),
        )
    )

    print("\n" + "=" * 45)
    print("LIBRARY SEED DATA VERIFICATION")
    print("=" * 45)

    print(f"Books: {book_count} (target: 40)")
    print(f"Members: {member_count} (target: 10)")
    print(f"Loans: {loan_count} (target: 25)")

    print(
        f"Historical late returns: "
        f"{historical_late_returns}"
    )

    print(
        f"Active overdue loans: "
        f"{active_overdue_loans}"
    )

    print("=" * 45)

    if (
        book_count >= 40
        and member_count >= 10
        and loan_count >= 25
    ):
        print("Seed count requirements satisfied.")
    else:
        print("Some seed count requirements are missing.")

    if historical_late_returns == 0 and active_overdue_loans == 0:
        print(
            "WARNING: No overdue examples found. "
            "Existing loans may already occupy all 25 slots."
        )


# --------------------------------------------------
# 7. MAIN FUNCTION
# --------------------------------------------------

def main():

    db = SessionLocal()

    try:

        print("\nStarting library seed process...\n")

        seed_books(db)
        db.flush()

        seed_members(db)
        db.flush()

        seed_loans(db)
        db.flush()

        db.commit()

        print("\nSeed data completed successfully!")

        verify_seed_data(db)

    except Exception as error:

        db.rollback()

        print(f"\nSeed failed: {error}")

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()
