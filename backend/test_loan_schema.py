
from uuid import uuid4

from pydantic import ValidationError

from schemas.loan_schema import CheckoutRequest


# Test 1: Valid book UUID
book_id = uuid4()

request = CheckoutRequest(
    book_id=book_id
)

assert request.book_id == book_id
print("Valid checkout request accepted!")


# Test 2: Invalid UUID
try:
    CheckoutRequest(book_id="invalid-book-id")
    raise AssertionError("Invalid UUID was accepted!")

except ValidationError:
    print("Invalid book UUID correctly rejected!")


# Test 3: Missing book ID
try:
    CheckoutRequest()
    raise AssertionError("Missing book ID was accepted!")

except ValidationError:
    print("Missing book ID correctly rejected!")
