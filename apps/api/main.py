"""
AI Code Review Bot — FastAPI Application Factory.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from core.config import settings
from core.database import init_db
from routers import webhooks, reviews, prompts, notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Creating database tables …")
    await init_db()
    logging.info("AI Code Review Bot ready")
    yield
    logging.info("Shutting down")


app = FastAPI(
    title="AI Code Review Bot",
    description="Production GitHub App — autonomous PR review with 4 Claude agents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(reviews.router)
app.include_router(prompts.router)
app.include_router(notifications.router)


@app.get("/")
async def root():
    return {
        "name": "AI Code Review Bot",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    checks = {"api": "ok"}
    try:
        from core.redis_client import redis_client
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    try:
        from core.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}
