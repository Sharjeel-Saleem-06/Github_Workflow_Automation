"""
Fix prompts library API — searchable collection of all generated fix prompts,
with feedback tracking (plan Section 8.5).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from models.models import Issue, Review, PullRequest, Repository

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptFeedback(BaseModel):
    helpful: bool


@router.post("/{issue_id}/feedback")
async def rate_prompt(
    issue_id: str,
    feedback: PromptFeedback,
    db: AsyncSession = Depends(get_db),
):
    """Track which generated prompts were actually useful — plan Section 8.5."""
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.is_helpful = feedback.helpful
    await db.commit()
    return {"status": "ok", "issue_id": issue_id, "helpful": feedback.helpful}


@router.get("")
async def list_prompts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    agent: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Issue)
        .join(Review)
        .join(PullRequest)
        .join(Repository)
        .where(Issue.generated_prompt.isnot(None))
        .where(Issue.generated_prompt != "")
        .options(
            selectinload(Issue.review)
            .selectinload(Review.pull_request)
            .selectinload(PullRequest.repository)
        )
        .order_by(desc(Issue.created_at))
    )

    if severity:
        query = query.where(Issue.severity == severity)
    if agent:
        query = query.where(Issue.agent_type == agent)
    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Issue.description.ilike(term),
                Issue.generated_prompt.ilike(term),
                Issue.file_path.ilike(term),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    issues = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "prompts": [
            {
                "id": str(i.id),
                "agent_type": i.agent_type,
                "severity": i.severity,
                "category": i.category,
                "file_path": i.file_path,
                "line_number": i.line_number,
                "description": i.description,
                "generated_prompt": i.generated_prompt,
                "repo": i.review.pull_request.repository.full_name if i.review and i.review.pull_request and i.review.pull_request.repository else "",
                "pr_number": i.review.pull_request.pr_number if i.review and i.review.pull_request else 0,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in issues
        ],
    }
