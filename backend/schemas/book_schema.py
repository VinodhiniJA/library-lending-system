
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator
)


# =====================================
# 1. CREATE BOOK SCHEMA
# =====================================

class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    total_copies: int = Field(ge=0)

    @field_validator("title", "author")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value


# =====================================
# 2. UPDATE BOOK SCHEMA
# =====================================

class BookUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255
    )

    author: str | None = Field(
        default=None,
        min_length=1,
        max_length=255
    )

    @field_validator("title", "author")
    @classmethod
    def validate_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value


# =====================================
# 3. BOOK RESPONSE SCHEMA
# =====================================

class BookResponse(BaseModel):
    id: UUID
    title: str
    author: str
    total_copies: int

    model_config = ConfigDict(from_attributes=True)


# =====================================
# 4. BOOK COPY RESPONSE SCHEMA
# =====================================

class BookCopyResponse(BaseModel):
    id: UUID
    book_id: UUID
    status: str

    model_config = ConfigDict(from_attributes=True)


# =====================================
# 5. ADD COPIES SCHEMA
# =====================================

class AddBookCopies(BaseModel):
    quantity: int = Field(ge=1, le=100)
