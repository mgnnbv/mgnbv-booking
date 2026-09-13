import asyncio
import json
import logging

import aio_pika

from app.core.config import settings
from app.email_sender import send_email
from app.templates import render

logger = logging.getLogger(__name__)

_SENSITIVE_PAYLOAD_KEYS = {"code"}


def _redact(payload: dict) -> dict:
    return {k: ("***" if k in _SENSITIVE_PAYLOAD_KEYS else v) for k, v in payload.items()}


async def _handle_message(event_type: str, payload: dict) -> None:
    rendered = render(event_type, payload)
    if rendered is None:
        logger.info("no template for event type=%s, skipping", event_type)
        return

    recipient = payload.get("owner_email")
    if not recipient:
        logger.info("event type=%s has no owner_email, skipping", event_type)
        return

    subject, body = rendered
    await send_email(recipient, subject, body)


async def run_consumer(stop_event: asyncio.Event) -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)

    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            settings.events_exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(settings.events_queue, durable=True)
        await queue.bind(exchange, routing_key="#")

        queue_iter = queue.iterator()
        try:
            while not stop_event.is_set():
                try:
                    message = await asyncio.wait_for(queue_iter.__anext__(), timeout=5)
                except asyncio.TimeoutError:
                    continue
                except StopAsyncIteration:
                    break

                async with message.process(ignore_processed=True):
                    event_type = message.routing_key
                    try:
                        payload = json.loads(message.body.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        logger.warning("skipping malformed message routing_key=%s", event_type)
                        continue

                    try:
                        await _handle_message(event_type, payload)
                    except Exception:
                        logger.exception(
                            "failed to process message routing_key=%s payload=%s",
                            event_type,
                            _redact(payload),
                        )
        finally:
            await queue_iter.close()
    finally:
        await connection.close()
