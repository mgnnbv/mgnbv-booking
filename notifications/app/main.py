import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.consumer import run_consumer

logger = logging.getLogger(__name__)

_stop_event = asyncio.Event()
_supervisor_task: asyncio.Task | None = None
_crash_timestamps: list[float] = []

_CRASH_WINDOW_SECONDS = 60
_CRASH_THRESHOLD = 3
_RESTART_DELAY_SECONDS = 5


async def _supervised_consumer(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await run_consumer(stop_event)
        except Exception:
            logger.exception("consumer crashed unexpectedly")
            _crash_timestamps.append(time.monotonic())
            if stop_event.is_set():
                break
            await asyncio.sleep(_RESTART_DELAY_SECONDS)


def _is_crash_looping() -> bool:
    cutoff = time.monotonic() - _CRASH_WINDOW_SECONDS
    while _crash_timestamps and _crash_timestamps[0] < cutoff:
        _crash_timestamps.pop(0)
    return len(_crash_timestamps) >= _CRASH_THRESHOLD


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supervisor_task
    _stop_event.clear()
    _crash_timestamps.clear()
    _supervisor_task = asyncio.create_task(_supervised_consumer(_stop_event))
    try:
        yield
    finally:
        _stop_event.set()
        await _supervisor_task


app = FastAPI(title="mgnbvbooking-notifications", lifespan=lifespan)


@app.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    if _is_crash_looping():
        return JSONResponse(status_code=503, content={"status": "error", "detail": "consumer is crash-looping"})
    if _supervisor_task is not None and _supervisor_task.done() and not _stop_event.is_set():
        return JSONResponse(status_code=503, content={"status": "error", "detail": "consumer supervisor died"})
    return JSONResponse(status_code=200, content={"status": "ok"})