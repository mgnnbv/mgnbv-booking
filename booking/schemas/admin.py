from decimal import Decimal

from pydantic import BaseModel


class AdminOverview(BaseModel):
    users_count: int
    properties_count: int
    bookings_count: int
    payments_count: int
    paid_amount_total: Decimal
