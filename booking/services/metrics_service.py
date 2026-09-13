import logging
from typing import Any

import httpx

from booking.core.config import settings
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


async def get_metrics_summary() -> MetricsSummary:
    try:
        async with httpx.AsyncClient(base_url=settings.prometheus_url, timeout=5.0) as client:
            values: dict[str, float | None] = {}
            for key, query in _QUERIES.items():
                response = await client.get("/api/v1/query", params={"query": query})
                response.raise_for_status()
                values[key] = _parse_scalar(response.json())
    except (httpx.HTTPError, ValueError):
        logger.exception("failed to fetch metrics from Prometheus")
        return MetricsSummary(available=False)

    error_ratio = values.get("error_ratio")
    avg_latency = values.get("avg_latency_seconds")
    p95_latency = values.get("p95_latency_seconds")

    return MetricsSummary(
        available=True,
        requests_per_second=values.get("requests_per_second"),
        error_rate_percent=error_ratio * 100 if error_ratio is not None else None,
        avg_latency_ms=avg_latency * 1000 if avg_latency is not None else None,
        p95_latency_ms=p95_latency * 1000 if p95_latency is not None else None,
    )
