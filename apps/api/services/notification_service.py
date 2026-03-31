"""
Notification service: publishes events via Redis Pub/Sub for real-time SSE streaming
and persists notifications to the database.
"""
import json
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from models.models import Notification
from core.redis_client import redis_client

logger = logging.getLogger(__name__)

CHANNEL = "notifications"


async def publish_notification(
    type: str,
    title: str,
    body: str,
    metadata: dict | None = None,
    db: AsyncSession | None = None,
):
    notification_id = str(uuid.uuid4())
    payload = {
        "id": notification_id,
        "type": type,
        "title": title,
        "body": body,
        "metadata": metadata or {},
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await redis_client.publish(CHANNEL, json.dumps(payload))
    logger.info(f"Published notification: {type} — {title}")

    if db:
        notif = Notification(
            id=uuid.UUID(notification_id),
            type=type,
            title=title,
            body=body,
            extra_data=metadata,
        )
        db.add(notif)
        await db.commit()

    return payload


async def notification_generator():
    """Async generator that yields SSE events from Redis Pub/Sub."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield f"data: {message['data']}\n\n"
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()
