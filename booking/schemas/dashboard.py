import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from booking.schemas.payment import OverduePaymentRead
from booking.schemas.property import PropertyRead


class UpcomingBookingEvent(BaseModel):
    booking_id: uuid.UUID
    property_id: uuid.UUID
    property_title: str
    tenant_id: uuid.UUID
    tenant_full_name: str
    event_type: str  # "check_in" | "check_out"
    event_date: date


class MonthlyIncomeSummary(BaseModel):
    year: int
    month: int
    total_paid: Decimal
    total_expected: Decimal


class DashboardResponse(BaseModel):
    """Один агрегирующий ответ для главного экрана мобилки — см. правило
    'меньше запросов': объекты, ближайшие заезды/выезды (7 дней), просрочки,
    сводка дохода за месяц одним запросом."""

    properties: list[PropertyRead]
    upcoming_events: list[UpcomingBookingEvent]
    overdue_payments: list[OverduePaymentRead]
    monthly_income: MonthlyIncomeSummary
