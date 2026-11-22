
import re
from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
    field_validator
)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Include at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Include at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Include at least one number")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Include at least one special character")
        return value


class VerifyEmail(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


class ResendOTP(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)
