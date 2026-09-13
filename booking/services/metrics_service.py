import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.config import settings
from booking.models.booking import Booking
from booking.models.enums import BookingStatus, PaymentStatus
from booking.models.payment import Payment
from booking.models.pending_registration import PendingRegistration
from booking.models.property import Property
from booking.models.user import User
from booking.schemas.metrics import MetricsSummary

logger = logging.getLogger(__name__)

_RANGE = "5m"

_QUERIES = {
    "requests_per_second": f"sum(rate(http_requests_total[{_RANGE}]))",
    "error_ratio": (
        f'sum(rate(http_requests_total{{status=~"4..|5.."}}[{_RANGE}])) '
        f"/ sum(rate(http_requests_total[{_RANGE}]))"
    ),
    "avg_latency_seconds": (
        f"sum(rate(http_request_duration_seconds_sum[{_RANGE}])) "
        f"/ sum(rate(http_request_duration_seconds_count[{_RANGE}]))"
    ),
    "p95_latency_seconds": (
        f"histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[{_RANGE}])) by (le))"
    ),
}


def _parse_scalar(payload: dict[str, Any]) -> float | None:
    result = payload.get("data", {}).get("result", [])
    if not result:
        return None
    try:
        value = float(result[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return value if value == value else None  # исключаем NaN (Prometheus отдаёт его при делении 0/0)


async def _fetch_prometheus_metrics() -> dict[str, float | None]:
    async with httpx.AsyncClient(base_url=settings.prometheus_url, timeout=5.0) as client:
        values: dict[str, float | None] = {}
        for key, query in _QUERIES.items():
            response = await client.get("/api/v1/query", params={"query": query})
            response.raise_for_status()
            values[key] = _parse_scalar(response.json())
        return values


async def _fetch_business_metrics(db: AsyncSession) -> dict[str, Any]:
    today = date.today()
    month_start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    total_users = await db.scalar(select(func.count()).select_from(User))
    new_users_last_7_days = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    )
    pending_registrations_count = await db.scalar(select(func.count()).select_from(PendingRegistration))
    total_properties_active = await db.scalar(
        select(func.count()).select_from(Property).where(Property.is_archived.is_(False))
    )
    total_bookings_active = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.status.in_([BookingStatus.PENDING, BookingStatus.ACTIVE]))
    )
    overdue_payments_count = await db.scalar(
        select(func.count())
        .select_from(Payment)
        .where(
            Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE]),
            Payment.due_date < today,
        )
    )
    total_revenue_this_month = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.PAID,
            Payment.paid_at >= month_start,
        )
    )

    return {
        "total_users": total_users or 0,
        "new_users_last_7_days": new_users_last_7_days or 0,
        "pending_registrations_count": pending_registrations_count or 0,
        "total_properties_active": total_properties_active or 0,
        "total_bookings_active": total_bookings_active or 0,
        "overdue_payments_count": overdue_payments_count or 0,
        "total_revenue_this_month": total_revenue_this_month or Decimal("0"),
    }


async def get_metrics_summary(db: AsyncSession) -> MetricsSummary:
    business = await _fetch_business_metrics(db)

    try:
        prom = await _fetch_prometheus_metrics()
    except (httpx.HTTPError, ValueError):
        logger.exception("failed to fetch metrics from Prometheus")
        return MetricsSummary(available=False, **business)

    error_ratio = prom.get("error_ratio")
    avg_latency = prom.get("avg_latency_seconds")
    p95_latency = prom.get("p95_latency_seconds")

    return MetricsSummary(
        available=True,
        requests_per_second=prom.get("requests_per_second"),
        error_rate_percent=error_ratio * 100 if error_ratio is not None else None,
        avg_latency_ms=avg_latency * 1000 if avg_latency is not None else None,
        p95_latency_ms=p95_latency * 1000 if p95_latency is not None else None,
        **business,
    )
