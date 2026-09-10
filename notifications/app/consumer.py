import asyncio
import json
import logging

import redis.asyncio as redis

from app.core.config import settings
from app.email_sender import send_email
from app.templates import render

logger = logging.getLogger(__name__)

_SENSITIVE_PAYLOAD_KEYS = {"code"}


def _redact(fields: dict[str, str]) -> dict[str, str]:
    try:
        payload = json.loads(fields.get("payload", "{}"))
    except json.JSONDecodeError:
        return fields
    redacted_payload = {k: ("***" if k in _SENSITIVE_PAYLOAD_KEYS else v) for k, v in payload.items()}
    return {**fields, "payload": json.dumps(redacted_payload)}


async def _ensure_group(client: redis.Redis) -> None:
    try:
        await client.xgroup_create(settings.notifications_stream, settings.consumer_group, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _handle_message(fields: dict[str, str]) -> None:
    event_type = fields.get("type")
    raw_payload = fields.get("payload")
    if not event_type or raw_payload is None:
        logger.warning("skipping malformed event: %s", fields)
        return

    payload = json.loads(raw_payload)
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
    client = redis.from_url(settings.redis_url, decode_responses=True)

    try:
        await _ensure_group(client)

        while not stop_event.is_set():
            try:
                response = await client.xreadgroup(
                    groupname=settings.consumer_group,
                    consumername=settings.consumer_name,
                    streams={settings.notifications_stream: ">"},
                    count=10,
                    block=5000,
                )
            except redis.RedisError:
                logger.exception("redis read failed, retrying in 5s")
                await asyncio.sleep(5)
                continue

            for _stream_name, messages in response:
                for message_id, message_fields in messages:
                    try:
                        await _handle_message(message_fields)
                    except Exception:
                        logger.exception(
                            "failed to process message id=%s fields=%s", message_id, _redact(message_fields)
                        )
                    finally:
                        await client.xack(settings.notifications_stream, settings.consumer_group, message_id)
    finally:
        await client.aclose()