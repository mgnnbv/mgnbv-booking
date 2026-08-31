import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from booking.models.enums import PropertyType, RentalType


class PropertyPhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    sort_order: int


class PropertyBase(BaseModel):
    title: str = Field(max_length=255)
    property_type: PropertyType
    address: str | None = None
    description: str | None = None
    default_rate: Decimal | None = None
    default_rental_type: RentalType | None = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    property_type: PropertyType | None = None
    address: str | None = None
    description: str | None = None
    default_rate: Decimal | None = None
    default_rental_type: RentalType | None = None
    is_archived: bool | None = None


class PropertyRead(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    photos: list[PropertyPhotoRead] = []
