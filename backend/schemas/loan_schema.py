
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# =====================================
# 1. CHECKOUT REQUEST SCHEMA
# =====================================

class CheckoutRequest(BaseModel):
    book_id: UUID


# =====================================
# 2. LOAN RESPONSE SCHEMA
# =====================================

class LoanResponse(BaseModel):
    id: UUID
    user_id: UUID
    copy_id: UUID

    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None

    status: str

    model_config = ConfigDict(from_attributes=True)
