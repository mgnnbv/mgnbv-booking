import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from booking.schemas.booking import BookingRead


class TenantBase(BaseModel):
    full_name: str = Field(max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    notes: str | None = None


class TenantCreate(TenantBase):
    passport_data: str | None = Field(
        default=None, description="Паспортные данные в открытом виде; шифруются перед сохранением"
    )


class TenantUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    passport_data: str | None = None


class TenantRead(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    has_passport_data: bool = False


class TenantDetailRead(TenantRead):
    bookings: list[BookingRead] = []