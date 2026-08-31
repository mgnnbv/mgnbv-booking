from fastapi import APIRouter

from booking.core.deps import CurrentUser, DbSession
from booking.schemas.dashboard import DashboardResponse
from booking.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(current_user: CurrentUser, db: DbSession) -> DashboardResponse:
    """Один агрегирующий запрос для главного экрана мобилки вместо 4 отдельных."""
    return await dashboard_service.build_dashboard(db, current_user.id)
