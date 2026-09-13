from fastapi import APIRouter

from booking.core.deps import AdminUser
from booking.schemas.metrics import MetricsSummary
from booking.services import metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    _: AdminUser,
) -> MetricsSummary:
    return await metrics_service.get_metrics_summary()
