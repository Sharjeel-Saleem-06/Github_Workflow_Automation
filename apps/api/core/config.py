import os
import base64
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GitHub App
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    MODEL_NAME: str = "claude-haiku-4-5-20251001"
    MAX_TOKENS_AGENT: int = 4096
    MAX_TOKENS_AGGREGATOR: int = 8192

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/reviewbot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # App
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def github_private_key_pem(self) -> str:
        """Decode base64-encoded PEM key, or return as-is if already PEM."""
        key = self.GITHUB_APP_PRIVATE_KEY
        if not key:
            return ""
        if key.startswith("-----BEGIN"):
            return key
        try:
            return base64.b64decode(key).decode("utf-8")
        except Exception:
            return key

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
