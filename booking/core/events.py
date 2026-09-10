import json
import logging
from typing import Any

import redis.asyncio as redis

from booking.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def publish_event(event_type: str, payload: dict[str, Any]) -> None:

    try:
        client = _get_client()
        await client.xadd(settings.notifications_stream, {"type": event_type, "payload": json.dumps(payload)})
    except redis.RedisError:
        logger.exception("failed to publish event type=%s", event_type)

async def close_event_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None