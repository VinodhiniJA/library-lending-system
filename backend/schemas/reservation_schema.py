
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReservationCreate(BaseModel):
    book_id: UUID


class ReservationResponse(BaseModel):
    id: UUID
    user_id: UUID
    book_id: UUID
    copy_id: UUID | None
    status: str
    created_at: datetime
    hold_expires_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
