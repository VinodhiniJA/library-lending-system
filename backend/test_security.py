
from core.security import (
    hash_password,
    verify_password,
    create_access_token
)


password = "TestPassword123!"

hashed = hash_password(password)

print("Password hashed successfully!")
print("Correct password:", verify_password(password, hashed))
print("Wrong password:", verify_password("WrongPassword", hashed))

token = create_access_token("test-user-123")

print("JWT created successfully:", bool(token))
