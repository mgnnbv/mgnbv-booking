from fastapi import FastAPI

from booking.api.routers import api_router
from booking.core.config import settings
from booking.core.exceptions import register_exception_handlers

app = FastAPI(title=settings.project_name)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
