from fastapi import APIRouter

from booking.api.routers import auth, bookings, dashboard, payments, properties, tenants

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(tenants.router)
api_router.include_router(bookings.router)
api_router.include_router(payments.router)
api_router.include_router(dashboard.router)
