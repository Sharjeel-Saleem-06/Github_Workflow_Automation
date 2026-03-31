"""
Celery tasks for async review processing.
When the webhook arrives, it returns 200 immediately and queues the review here.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.celery_app import celery_app
from core.config import settings
from models.models import Repository, PullRequest, Review, Issue, Notification
from services.github_client import GitHubClient
from services.review_orchestrator import ReviewOrchestrator
from services.notification_service import publish_notification

logger = logging.getLogger(__name__)


def _make_session_factory():
    """Create a fresh engine + session factory bound to the CURRENT event loop."""
    eng = create_async_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    return async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False), eng


def _run_async(coro):
    """Helper to run async code inside a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_pr_review(self, payload: dict):
    """Main task: review a PR opened/updated event."""
    _run_async(_process_pr_review_async(payload))


async def _process_pr_review_async(payload: dict):
    installation_id = payload["installation_id"]
    owner = payload["owner"]
    repo_name = payload["repo"]
    pr_number = payload["pr_number"]
    pr_title = payload["pr_title"]
    pr_author = payload["pr_author"]
    head_sha = payload["head_sha"]
    repo_github_id = payload["repo_id"]
    full_name = f"{owner}/{repo_name}"

    task_session, task_engine = _make_session_factory()

    async with task_session() as db:
        from sqlalchemy import select

        repo_result = await db.execute(
            select(Repository).where(Repository.github_id == repo_github_id)
        )
        repo = repo_result.scalar_one_or_none()
        if not repo:
            repo = Repository(
                github_id=repo_github_id,
                full_name=full_name,
                installation_id=installation_id,
            )
            db.add(repo)
            await db.flush()

        pr_result = await db.execute(
            select(PullRequest).where(
                PullRequest.repo_id == repo.id,
                PullRequest.pr_number == pr_number,
            )
        )
        pr = pr_result.scalar_one_or_none()
        if not pr:
            pr = PullRequest(
                repo_id=repo.id,
                pr_number=pr_number,
                title=pr_title,
                author=pr_author,
                head_sha=head_sha,
            )
            db.add(pr)
            await db.flush()
        else:
            pr.head_sha = head_sha
            pr.title = pr_title

        review = Review(pr_id=pr.id, status="running", trigger_type="pr_webhook")
        db.add(review)
        await db.commit()
        review_id = review.id

    pr_context = {
        "title": pr_title,
        "repo": full_name,
        "author": pr_author,
        "files_changed": payload.get("files_changed", 0),
        "additions": payload.get("additions", 0),
        "deletions": payload.get("deletions", 0),
    }

    gh = GitHubClient(installation_id)
    orchestrator = ReviewOrchestrator(gh)

    result = await orchestrator.run_review(owner, repo_name, pr_number, head_sha, pr_context)

    async with task_session() as db:
        from sqlalchemy import select

        review_obj = await db.get(Review, review_id)
        review_obj.status = "completed"
        review_obj.agents_output = result.get("agents_output")
        review_obj.final_summary = result.get("summary_markdown", "")
        review_obj.critical_count = int(result.get("total_critical", 0) or 0)
        review_obj.warning_count = int(result.get("total_high", 0) or 0) + int(result.get("total_medium", 0) or 0)
        review_obj.info_count = int(result.get("total_low", 0) or 0)
        review_obj.total_issues = review_obj.critical_count + review_obj.warning_count + review_obj.info_count
        review_obj.tokens_used = int(result.get("total_tokens", 0) or 0)
        review_obj.cost_usd = float(result.get("total_cost_usd", 0.0) or 0.0)
        review_obj.completed_at = datetime.now(timezone.utc)

        for fp in result.get("fix_prompts", []):
            issue = Issue(
                review_id=review_id,
                agent_type=fp.get("agent", "unknown"),
                severity=fp.get("severity", "medium"),
                category=fp.get("issue", ""),
                file_path=fp.get("file", ""),
                line_number=int(fp["line"]) if fp.get("line") else None,
                description=fp.get("issue", ""),
                suggested_fix=fp.get("prompt", ""),
                generated_prompt=fp.get("prompt", ""),
            )
            db.add(issue)

        await db.commit()

    async with task_session() as db:
        await publish_notification(
            type="review_completed",
            title=f"Review complete: {full_name}#{pr_number}",
            body=f"Found {result.get('total_critical', 0)} critical, "
                 f"{result.get('total_high', 0)} high issues. "
                 f"Cost: ${result.get('total_cost_usd', 0):.4f}",
            metadata={
                "review_id": str(review_id),
                "repo": full_name,
                "pr_number": pr_number,
                "verdict": result.get("verdict", ""),
            },
            db=db,
        )

    verdict = result.get("verdict", "")
    total_issues = int(result.get("total_critical", 0) or 0) + int(result.get("total_high", 0) or 0) + int(result.get("total_medium", 0) or 0) + int(result.get("total_low", 0) or 0)
    check_conclusion = "action_required" if verdict == "CHANGES_REQUESTED" else "success"
    check_title = f"{'CHANGES REQUESTED' if verdict == 'CHANGES_REQUESTED' else 'APPROVED'} — {total_issues} issue(s) found"
    check_summary = (
        f"**Verdict:** {verdict}\n\n"
        f"| Severity | Count |\n|---|---|\n"
        f"| Critical | {result.get('total_critical', 0)} |\n"
        f"| High | {result.get('total_high', 0)} |\n"
        f"| Medium | {result.get('total_medium', 0)} |\n"
        f"| Low | {result.get('total_low', 0)} |\n\n"
        f"**Cost:** ${result.get('total_cost_usd', 0):.4f} | **Tokens:** {result.get('total_tokens', 0)}\n\n"
        f"See the PR comments for detailed inline findings and fix prompts."
    )

    try:
        await gh.create_check_run(
            owner, repo_name, head_sha,
            status="completed",
            conclusion=check_conclusion,
            title=check_title,
            summary=check_summary,
        )
    except Exception as e:
        logger.warning(f"Failed to update check run: {e}")

    await task_engine.dispose()
    logger.info(f"Review completed for {full_name}#{pr_number}: {verdict}")


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=15,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_senior_comments(self, payload: dict):
    """Task: process senior dev change-request comments."""
    _run_async(_process_senior_comments_async(payload))


async def _process_senior_comments_async(payload: dict):
    from agents.senior_comment import SeniorCommentAgent
    from models.models import SeniorComment

    installation_id = payload["installation_id"]
    owner = payload["owner"]
    repo_name = payload["repo"]
    pr_number = payload["pr_number"]
    pr_title = payload["pr_title"]
    reviewer_login = payload["reviewer_login"]
    comments = payload["comments"]

    gh = GitHubClient(installation_id)

    diff = ""
    try:
        diff = await gh.get_pr_diff(owner, repo_name, pr_number)
    except Exception:
        pass

    agent = SeniorCommentAgent()
    result = await agent.handle(pr_title, comments, diff)

    full_name = f"{owner}/{repo_name}"

    task_session, task_engine = _make_session_factory()

    async with task_session() as db:
        from sqlalchemy import select

        pr_result = await db.execute(
            select(PullRequest).join(Repository).where(
                Repository.full_name == full_name,
                PullRequest.pr_number == pr_number,
            )
        )
        pr = pr_result.scalar_one_or_none()
        if not pr:
            await task_engine.dispose()
            return

        for handled in result.get("handled_comments", []):
            sc = SeniorComment(
                pr_id=pr.id,
                reviewer_login=reviewer_login,
                body=handled.get("original_comment", ""),
                file_path=handled.get("file"),
                guidance=handled.get("guidance", ""),
                generated_prompt=handled.get("fix_prompt", ""),
            )
            db.add(sc)

        await db.commit()

    async with task_session() as db:
        await publish_notification(
            type="senior_feedback",
            title=f"Senior feedback on {full_name}#{pr_number}",
            body=f"{reviewer_login} requested changes. "
                 f"{len(result.get('handled_comments', []))} prompts generated.",
            metadata={
                "repo": full_name,
                "pr_number": pr_number,
                "reviewer": reviewer_login,
            },
            db=db,
        )

    await task_engine.dispose()
