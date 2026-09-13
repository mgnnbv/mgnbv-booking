import json
import logging
from typing import Any

import aio_pika

from booking.core.config import settings

logger = logging.getLogger(__name__)

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None


async def _get_exchange() -> aio_pika.abc.AbstractExchange:
    global _connection, _exchange
    if _exchange is None:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await _connection.channel()
        _exchange = await channel.declare_exchange(
            settings.events_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
    return _exchange


async def publish_event(event_type: str, payload: dict[str, Any]) -> None:
    try:
        exchange = await _get_exchange()
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=event_type)
    except Exception:
        logger.exception("failed to publish event type=%s", event_type)


async def close_event_client() -> None:
    global _connection, _exchange
    if _connection is not None:
        await _connection.close()
        _connection = None
        _exchange = None
