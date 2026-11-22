from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SettingsUpdate(BaseModel):
    loan_period_days: int | None = Field(default=None, gt=0)
    fine_per_day: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    max_fine_amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    max_active_loans: int | None = Field(default=None, gt=0)
    hold_period_hours: int | None = Field(default=None, gt=0)
    fine_block_threshold: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class SettingsResponse(BaseModel):
    id: int
    loan_period_days: int
    fine_per_day: Decimal
    max_fine_amount: Decimal
    max_active_loans: int
    hold_period_hours: int
    fine_block_threshold: Decimal
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)