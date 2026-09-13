from decimal import Decimal

from pydantic import BaseModel


class MetricsSummary(BaseModel):
    available: bool
    requests_per_second: float | None = None
    error_rate_percent: float | None = None
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None

    # Бизнес-метрики по всей системе (не только текущего юзера) — считаются
    # из БД напрямую и не зависят от доступности Prometheus.
    total_users: int
    new_users_last_7_days: int
    pending_registrations_count: int
    total_properties_active: int
    total_bookings_active: int
    overdue_payments_count: int
    total_revenue_this_month: Decimal
