
from pydantic import ValidationError

from schemas.book_schema import (
    BookCreate,
    BookUpdate,
    AddBookCopies
)


# Test 1: Valid book
book = BookCreate(
    title="Python Programming",
    author="John Smith",
    total_copies=5
)

print("Valid book:", book.title)


# Test 2: Negative copies
try:
    BookCreate(
        title="Python Programming",
        author="John Smith",
        total_copies=-2
    )

except ValidationError:
    print("Negative copies correctly rejected!")


# Test 3: Empty title
try:
    BookCreate(
        title="   ",
        author="John Smith",
        total_copies=3
    )

except ValidationError:
    print("Empty title correctly rejected!")


# Test 4: Update book
updated_book = BookUpdate(
    title="Advanced Python Programming"
)

print("Updated title:", updated_book.title)


# Test 5: Invalid copy quantity
try:
    AddBookCopies(quantity=0)

except ValidationError:
    print("Invalid copy quantity correctly rejected!")
