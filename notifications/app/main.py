import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.consumer import run_consumer

_stop_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _stop_event.clear()
    task = asyncio.create_task(run_consumer(_stop_event))
    try:
        yield
    finally:
        _stop_event.set()
        await task


app = FastAPI(title="mgnbvbooking-notifications", lifespan=lifespan)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
