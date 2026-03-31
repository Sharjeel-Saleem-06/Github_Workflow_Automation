"""
SSE endpoint for real-time notifications + REST for notification history.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from core.database import get_db
from models.models import Notification
from services.notification_service import notification_generator

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/stream")
async def notification_stream():
    """SSE stream for real-time notifications."""
    return EventSourceResponse(notification_generator())


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).order_by(desc(Notification.created_at))
    if unread_only:
        query = query.where(Notification.is_read == False)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "metadata": n.extra_data,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
    }


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id)
        .values(is_read=True)
        .returning(Notification.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.commit()
    return {"status": "ok"}


@router.post("/mark-all-read")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification).where(Notification.is_read == False).values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}
