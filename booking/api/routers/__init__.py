from fastapi import APIRouter

from booking.core.config import settings
from booking.api.routers import admin, auth, bookings, dashboard, metrics, payments, properties, tenants

api_router = APIRouter(prefix=settings.api_v1_prefix)
api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(tenants.router)
api_router.include_router(bookings.router)
api_router.include_router(payments.router)
api_router.include_router(dashboard.router)
api_router.include_router(metrics.router)
api_router.include_router(admin.router)
