import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    email_verified: bool
    phone: str | None
    full_name: str | None
    created_at: datetime
    updated_at: datetime