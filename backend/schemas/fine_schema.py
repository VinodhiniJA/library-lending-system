
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class FinePaymentCreate(BaseModel):
    amount: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2
    )


class FinePaymentResponse(BaseModel):
    id: UUID
    fine_id: UUID
    amount: Decimal

    model_config = {"from_attributes": True}


class FineResponse(BaseModel):
    id: UUID
    loan_id: UUID
    amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
