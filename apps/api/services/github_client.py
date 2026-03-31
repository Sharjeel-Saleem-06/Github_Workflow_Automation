"""
GitHub API client: fetch PR diffs, post inline review comments, and post summary comments.
Uses installation access tokens from github_auth.
"""
import httpx
from typing import Optional

from .github_auth import get_installation_token

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, installation_id: int):
        self.installation_id = installation_id
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        if not self._token:
            self._token = await get_installation_token(self.installation_id)
        return self._token

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={
                    **self._headers(token),
                    "Accept": "application/vnd.github.diff",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.text

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                headers=self._headers(token),
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        body: str,
        path: str,
        line: int,
        side: str = "RIGHT",
    ) -> dict:
        """Post an inline review comment on a specific line of the diff."""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                headers=self._headers(token),
                json={
                    "body": body,
                    "commit_id": commit_sha,
                    "path": path,
                    "line": line,
                    "side": side,
                },
                timeout=30.0,
            )
            if resp.status_code == 422:
                return await self.post_issue_comment(owner, repo, pr_number, body)
            resp.raise_for_status()
            return resp.json()

    async def post_issue_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict:
        """Post a general comment on the PR (not inline)."""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=self._headers(token),
                json={"body": body},
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_pr_review_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict]:
        """Fetch all review comments on a PR (for senior comment processing)."""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                headers=self._headers(token),
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def post_pr_review_batch(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        inline_comments: list[dict],
    ) -> dict:
        """
        Post a proper PR review with multiple inline comments in one API call.
        This is the real GitHub review — appears as a proper code review.
        """
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers=self._headers(token),
                json={
                    "commit_id": commit_sha,
                    "event": "COMMENT",
                    "body": "🤖 AI Code Review — See inline comments below",
                    "comments": [
                        {
                            "path": c["path"],
                            "line": c["line"],
                            "body": c["body"],
                            "side": "RIGHT",
                        }
                        for c in inline_comments
                        if c.get("line")
                    ],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_pr_details(self, owner: str, repo: str, pr_number: int) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._headers(token),
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_check_run(
        self,
        owner: str,
        repo: str,
        head_sha: str,
        status: str = "in_progress",
        conclusion: str | None = None,
        title: str = "AI Code Review",
        summary: str = "",
    ) -> dict:
        """
        Create or complete a GitHub Check Run.
        - status: "queued", "in_progress", "completed"
        - conclusion (only when completed): "success", "failure", "neutral", "action_required"
        """
        token = await self._get_token()
        body = {
            "name": "AI Code Review Bot",
            "head_sha": head_sha,
            "status": status,
            "output": {
                "title": title,
                "summary": summary,
            },
        }
        if status == "in_progress":
            from datetime import datetime, timezone
            body["started_at"] = datetime.now(timezone.utc).isoformat()

        if status == "completed" and conclusion:
            body["conclusion"] = conclusion
            from datetime import datetime, timezone
            body["completed_at"] = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/check-runs",
                headers=self._headers(token),
                json=body,
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()
