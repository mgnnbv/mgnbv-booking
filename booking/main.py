from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from booking.api.routers import api_router
from booking.core.config import settings
from booking.core.exceptions import register_exception_handlers

app = FastAPI(title=settings.project_name)

# Открыто для локальной разработки фронтенда (статический SPA на другом порту).
# JWT передаётся заголовком Authorization, а не cookie, поэтому credentials не нужны.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
