"""
GitHub App authentication: JWT generation + installation access tokens.

Flow:
  1. Generate a short-lived JWT signed with the App's private key
  2. Exchange the JWT for an installation access token scoped to the repo
  3. Use that token for all GitHub API calls
"""
import time
import jwt
import httpx

from core.config import settings

GITHUB_API = "https://api.github.com"


def generate_jwt() -> str:
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": settings.GITHUB_APP_ID,
    }
    pem = settings.github_private_key_pem
    return jwt.encode(payload, pem, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    token_jwt = generate_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {token_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]
