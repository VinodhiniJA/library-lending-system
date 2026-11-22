
from pydantic import ValidationError
from schemas.user_schema import UserRegister


# Test 1: Valid registration
valid_user = UserRegister(
    name="Priya",
    email="priya@example.com",
    password="SecurePass@123"
)

print("Valid registration:", valid_user.name)


# Test 2: Invalid email
try:
    UserRegister(
        name="Priya",
        email="invalid-email",
        password="SecurePass@123"
    )

except ValidationError:
    print("Invalid email correctly rejected!")


# Test 3: Short password
try:
    UserRegister(
        name="Priya",
        email="priya@example.com",
        password="123"
    )

except ValidationError:
    print("Short password correctly rejected!")
