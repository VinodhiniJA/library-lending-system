
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db

from models.book import Book
from models.book_copy import BookCopy
from models.user import User

from schemas.book_schema import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookCopyResponse,
    AddBookCopies
)

from core.dependencies import (
    get_current_user,
    require_librarian
)


router = APIRouter(
    prefix="/books",
    tags=["Book Management"]
)


# =====================================
# CREATE BOOK - LIBRARIAN
# =====================================

@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED
)
def create_book(
    book_data: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    try:
        new_book = Book(
            title=book_data.title,
            author=book_data.author,
            total_copies=book_data.total_copies
        )

        db.add(new_book)
        db.flush()

        for _ in range(book_data.total_copies):
            db.add(
                BookCopy(
                    book_id=new_book.id,
                    status="AVAILABLE"
                )
            )

        db.commit()
        db.refresh(new_book)

        return new_book

    except Exception:
        db.rollback()
        raise


# =====================================
# VIEW ALL BOOKS
# =====================================

@router.get(
    "",
    response_model=list[BookResponse]
)
def get_all_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.scalars(
        select(Book).order_by(Book.title)
    ).all()


# =====================================
# DYNAMIC BOOK AVAILABILITY
# =====================================

@router.get("/availability")
def get_book_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = db.execute(
        select(
            Book.id,
            Book.title,
            Book.author,
            func.count(BookCopy.id).label("total"),
            func.count(BookCopy.id).filter(
                BookCopy.status == "AVAILABLE"
            ).label("available"),
            func.count(BookCopy.id).filter(
                BookCopy.status == "BORROWED"
            ).label("borrowed"),
            func.count(BookCopy.id).filter(
                BookCopy.status == "HELD"
            ).label("held")
        )
        .outerjoin(
            BookCopy,
            BookCopy.book_id == Book.id
        )
        .group_by(
            Book.id,
            Book.title,
            Book.author
        )
        .order_by(Book.title)
    ).all()

    return [
        {
            "id": str(row.id),
            "title": row.title,
            "author": row.author,
            "total_copies": row.total,
            "available_copies": row.available,
            "borrowed_copies": row.borrowed,
            "held_copies": row.held
        }
        for row in rows
    ]


# =====================================
# VIEW SINGLE BOOK
# =====================================

@router.get(
    "/{book_id}",
    response_model=BookResponse
)
def get_book(
    book_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    book = db.get(Book, book_id)

    if book is None:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    return book


# =====================================
# UPDATE BOOK - LIBRARIAN
# =====================================

@router.put(
    "/{book_id}",
    response_model=BookResponse
)
def update_book(
    book_id: UUID,
    book_data: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    try:
        book = db.get(Book, book_id)

        if book is None:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        updates = book_data.model_dump(
            exclude_unset=True,
            exclude_none=True
        )

        # Copy counts must be changed using
        # the dedicated add-copies endpoint.
        updates.pop("total_copies", None)

        for field, value in updates.items():
            setattr(book, field, value)

        db.commit()
        db.refresh(book)

        return book

    except Exception:
        db.rollback()
        raise


# =====================================
# ADD BOOK COPIES - LIBRARIAN
# =====================================

@router.post(
    "/{book_id}/copies",
    response_model=list[BookCopyResponse],
    status_code=status.HTTP_201_CREATED
)
def add_book_copies(
    book_id: UUID,
    copy_data: AddBookCopies,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_librarian)
):
    try:
        if copy_data.quantity < 1:
            raise HTTPException(
                status_code=422,
                detail="Quantity must be at least 1"
            )

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

        new_copies = []

        for _ in range(copy_data.quantity):
            copy = BookCopy(
                book_id=book.id,
                status="AVAILABLE"
            )
            db.add(copy)
            new_copies.append(copy)

        book.total_copies += copy_data.quantity

        db.commit()

        for copy in new_copies:
            db.refresh(copy)

        return new_copies

    except Exception:
        db.rollback()
        raise
