
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models.user import User
from core.security import hash_password


def create_librarian():
    print("\n=== Create Librarian Account ===")

    name = input("Enter librarian name: ").strip()
    email = input("Enter librarian email: ").strip().lower()

    if len(name) < 2 or "@" not in email:
        print("Invalid name or email.")
        return

    password = getpass("Enter librarian password: ")
    confirm_password = getpass("Confirm librarian password: ")

    if password != confirm_password:
        print("Passwords do not match.")
        return

    if not 8 <= len(password) <= 128:
        print("Password must contain 8 to 128 characters.")
        return

    db = SessionLocal()

    try:
        existing_user = db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user:
            print("An account with this email already exists.")
            return

        librarian = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="LIBRARIAN",
            is_active=True
        )

        db.add(librarian)
        db.commit()

        print("\nLibrarian account created successfully!")
        print("Email:", email)
        print("Role: LIBRARIAN")

    except IntegrityError:
        db.rollback()
        print("An account with this email already exists.")

    except Exception:
        db.rollback()
        print("Account creation failed.")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_librarian()
