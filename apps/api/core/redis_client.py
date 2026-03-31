import redis.asyncio as aioredis

from .config import settings

_extra_kwargs = {}
if settings.REDIS_URL.startswith("rediss://"):
    _extra_kwargs["ssl_cert_reqs"] = None

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=10,
    **_extra_kwargs,
)


async def get_redis() -> aioredis.Redis:
    return redis_client
