import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from booking.models.enums import PaymentStatus, PaymentType


class PaymentCreate(BaseModel):
    payment_type: PaymentType = PaymentType.RENT
    amount: Decimal
    due_date: date
    payment_method: str | None = Field(default=None, max_length=50)
    comment: str | None = None


class PaymentUpdate(BaseModel):
    status: PaymentStatus | None = None
    amount: Decimal | None = None
    due_date: date | None = None
    paid_at: datetime | None = None
    payment_method: str | None = Field(default=None, max_length=50)
    comment: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    payment_type: PaymentType
    status: PaymentStatus
    amount: Decimal
    due_date: date
    paid_at: datetime | None
    payment_method: str | None
    comment: str | None
    created_at: datetime


class OverduePaymentRead(PaymentRead):
    # Денормализованные поля для дашборда/списка просрочек мобилки —
    # чтобы не заставлять клиент делать доп. запрос за каждым booking/property.
    property_title: str
    tenant_full_name: str
