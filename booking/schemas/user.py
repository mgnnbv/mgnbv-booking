import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from booking.models.enums import UserRole

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    phone: str | None
    full_name: str | None
    role: UserRole
    created_at: datetime
    updated_at: datetime


class UserRoleUpdate(BaseModel):
    role: UserRole
