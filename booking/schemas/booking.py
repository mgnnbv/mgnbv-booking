import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from booking.models.enums import BookingStatus, RentalType


class BookingBase(BaseModel):
    property_id: uuid.UUID
    tenant_id: uuid.UUID
    rental_type: RentalType
    start_date: date
    end_date: date | None = None
    rent_amount: Decimal
    deposit_amount: Decimal | None = None
    monthly_payment_day: int | None = Field(default=None, ge=1, le=31)
    notes: str | None = None

    @model_validator(mode="after")
    def check_dates(self) -> "BookingBase":
        if self.end_date is not None and self.end_date <= self.start_date:
            raise ValueError("end_date должна быть позже start_date")
        return self


class BookingCreate(BookingBase):
    status: BookingStatus = BookingStatus.PENDING


class BookingUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = None
    deposit_amount: Decimal | None = None
    monthly_payment_day: int | None = Field(default=None, ge=1, le=31)
    status: BookingStatus | None = None
    notes: str | None = None


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    tenant_id: uuid.UUID
    rental_type: RentalType
    status: BookingStatus
    start_date: date
    end_date: date | None
    rent_amount: Decimal
    deposit_amount: Decimal | None
    monthly_payment_day: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
