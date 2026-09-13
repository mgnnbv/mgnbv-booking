from pydantic import BaseModel


class MetricsSummary(BaseModel):
    available: bool
    requests_per_second: float | None = None
    error_rate_percent: float | None = None
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None
