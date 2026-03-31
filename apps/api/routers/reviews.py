"""
REST API endpoints for review history and dashboard stats.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from models.models import Review, PullRequest, Repository, Issue, SeniorComment

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard overview statistics — plan Section 6.3."""
    total_reviews = (await db.execute(select(func.count(Review.id)))).scalar() or 0
    total_issues = (await db.execute(select(func.count(Issue.id)))).scalar() or 0
    total_repos = (await db.execute(select(func.count(Repository.id)))).scalar() or 0
    total_prs = (await db.execute(select(func.count(PullRequest.id)))).scalar() or 0

    critical = (await db.execute(
        select(func.count(Issue.id)).where(Issue.severity == "critical")
    )).scalar() or 0
    warning = (await db.execute(
        select(func.count(Issue.id)).where(Issue.severity == "warning")
    )).scalar() or 0
    info = (await db.execute(
        select(func.count(Issue.id)).where(Issue.severity == "info")
    )).scalar() or 0

    total_cost = (await db.execute(select(func.sum(Review.cost_usd)))).scalar() or 0.0
    total_tokens = (await db.execute(select(func.sum(Review.tokens_used)))).scalar() or 0

    recent_result = await db.execute(
        select(Review)
        .join(PullRequest)
        .join(Repository)
        .options(selectinload(Review.pull_request).selectinload(PullRequest.repository))
        .order_by(desc(Review.started_at))
        .limit(5)
    )
    recent = recent_result.scalars().all()

    return {
        "total_reviews": total_reviews,
        "total_issues": total_issues,
        "total_repos": total_repos,
        "total_prs": total_prs,
        "issues_by_severity": {"critical": critical, "warning": warning, "info": info},
        "total_cost_usd": round(float(total_cost), 4),
        "total_tokens": total_tokens,
        "recent_reviews": [_serialize_review(r) for r in recent],
    }


@router.get("")
async def list_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Review)
        .join(PullRequest)
        .join(Repository)
        .options(selectinload(Review.pull_request).selectinload(PullRequest.repository))
        .order_by(desc(Review.started_at))
    )

    if status:
        query = query.where(Review.status == status)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "reviews": [_serialize_review(r) for r in reviews],
    }


@router.get("/{review_id}")
async def get_review(review_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review)
        .where(Review.id == review_id)
        .options(
            selectinload(Review.issues),
            selectinload(Review.pull_request).selectinload(PullRequest.repository),
            selectinload(Review.pull_request).selectinload(PullRequest.senior_comments),
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    data = _serialize_review(review)
    data["issues"] = [
        {
            "id": str(i.id),
            "agent_type": i.agent_type,
            "severity": i.severity,
            "category": i.category,
            "file_path": i.file_path,
            "line_number": i.line_number,
            "description": i.description,
            "suggested_fix": i.suggested_fix,
            "generated_prompt": i.generated_prompt,
        }
        for i in review.issues
    ]
    data["senior_comments"] = [
        {
            "id": str(sc.id),
            "reviewer_login": sc.reviewer_login,
            "body": sc.body,
            "file_path": sc.file_path,
            "guidance": sc.guidance,
            "generated_prompt": sc.generated_prompt,
        }
        for sc in review.pull_request.senior_comments
    ]
    return data


def _serialize_review(r: Review) -> dict:
    pr = r.pull_request
    repo = pr.repository if pr else None
    return {
        "id": str(r.id),
        "status": r.status,
        "trigger_type": r.trigger_type,
        "verdict": (r.agents_output or {}).get("verdict", "") if isinstance(r.agents_output, dict) else "",
        "final_summary": r.final_summary,
        "critical_count": r.critical_count,
        "warning_count": r.warning_count,
        "info_count": r.info_count,
        "tokens_used": r.tokens_used,
        "cost_usd": r.cost_usd,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "pr": {
            "number": pr.pr_number,
            "title": pr.title,
            "author": pr.author,
            "head_sha": pr.head_sha,
        } if pr else None,
        "repo": {
            "full_name": repo.full_name,
        } if repo else None,
    }
