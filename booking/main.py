from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from booking.api.routers import api_router
from booking.core.config import settings
from booking.core.events import close_event_client
from booking.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_event_client()


app = FastAPI(title=settings.project_name, lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, include_in_schema=False)

register_exception_handlers(app)
app.include_router(api_router)

Path(settings.photos_storage_path).mkdir(parents=True, exist_ok=True)
app.mount(
    settings.photos_public_base_url,
    StaticFiles(directory=settings.photos_storage_path),
    name="property_photos",
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}