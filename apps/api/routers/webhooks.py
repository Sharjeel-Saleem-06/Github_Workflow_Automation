"""
GitHub webhook receiver with HMAC-SHA256 verification + idempotency.
Returns 200 immediately and queues the review task via Celery.
"""
import hmac
import hashlib
import logging
import asyncio

from fastapi import APIRouter, Request, HTTPException, Header

from core.config import settings
from core.redis_client import redis_client
from services.github_client import GitHubClient
from tasks.review_tasks import process_pr_review, process_senior_comments

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(payload_body: bytes, signature: str) -> bool:
    """HMAC-SHA256 verification — NEVER skip this in production."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
    x_github_delivery: str = Header(default=""),
):
    body = await request.body()

    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Idempotency — prevent duplicate processing via X-GitHub-Delivery header
    if x_github_delivery:
        idempotency_key = f"webhook:processed:{x_github_delivery}"
        if await redis_client.exists(idempotency_key):
            return {"status": "already_processed", "delivery": x_github_delivery}
        await redis_client.setex(idempotency_key, 86400, "1")  # 24h TTL

    payload = await request.json()

    if x_github_event == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            pr = payload["pull_request"]
            repo = payload["repository"]
            installation = payload.get("installation", {})

            task_payload = {
                "installation_id": installation.get("id", 0),
                "owner": repo["owner"]["login"],
                "repo": repo["name"],
                "repo_id": repo["id"],
                "pr_number": pr["number"],
                "pr_title": pr["title"],
                "pr_author": pr["user"]["login"],
                "head_sha": pr["head"]["sha"],
                "files_changed": pr.get("changed_files", 0),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
            }

            process_pr_review.apply_async(
                args=[task_payload],
                queue="high",
                retry=True,
                retry_policy={
                    "max_retries": 3,
                    "interval_start": 30,
                    "interval_step": 60,
                },
            )
            logger.info(f"Queued review for {repo['full_name']}#{pr['number']}")

            asyncio.create_task(_set_pending_check(
                installation.get("id", 0),
                repo["owner"]["login"],
                repo["name"],
                pr["head"]["sha"],
            ))

            return {"status": "queued", "pr": pr["number"], "delivery": x_github_delivery}

    elif x_github_event == "pull_request_review":
        action = payload.get("action", "")
        review = payload.get("review", {})
        if action == "submitted" and review.get("state") == "changes_requested":
            pr = payload["pull_request"]
            repo = payload["repository"]
            installation = payload.get("installation", {})

            comments = []
            if review.get("body"):
                comments.append({
                    "body": review["body"],
                    "file": None,
                    "line": None,
                })

            task_payload = {
                "installation_id": installation.get("id", 0),
                "owner": repo["owner"]["login"],
                "repo": repo["name"],
                "pr_number": pr["number"],
                "pr_title": pr["title"],
                "reviewer_login": review["user"]["login"],
                "comments": comments,
            }

            process_senior_comments.apply_async(
                args=[task_payload],
                queue="high",
                retry=True,
                retry_policy={"max_retries": 2, "interval_start": 15},
            )
            logger.info(
                f"Queued senior comment processing for "
                f"{repo['full_name']}#{pr['number']} by {review['user']['login']}"
            )

            return {"status": "queued_senior_review", "pr": pr["number"]}

    return {"status": "ignored"}


async def _set_pending_check(installation_id: int, owner: str, repo: str, head_sha: str):
    """Fire-and-forget: create an in_progress check run so the PR shows a spinner."""
    try:
        gh = GitHubClient(installation_id)
        await gh.create_check_run(
            owner, repo, head_sha,
            status="in_progress",
            title="AI Code Review in progress...",
            summary="Running 4 specialist AI agents: Color/Constants, Logic/Bugs, Best Practices, Security. Results in ~60 seconds.",
        )
        logger.info(f"Set pending check on {owner}/{repo}@{head_sha[:8]}")
    except Exception as e:
        logger.warning(f"Failed to set pending check: {e}")
