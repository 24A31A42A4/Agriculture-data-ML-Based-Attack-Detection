"""
Redis async connection pool.

Used for:
- Nonce storage (replay attack protection)
- Rate limiting (sliding window counters)
- Session/token caching
"""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

# ── Connection Pool ──────────────────────────────────────────────────────────

redis_pool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
    decode_responses=True,
)


def get_redis_client() -> aioredis.Redis:
    """Create a Redis client from the shared connection pool."""
    return aioredis.Redis(connection_pool=redis_pool)


# ── FastAPI Dependency ───────────────────────────────────────────────────────

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """
    Yield a Redis client for use in route handlers.

    Usage:
        @router.post("/ingest")
        async def ingest(redis: Redis = Depends(get_redis)):
            ...
    """
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


# ── Lifecycle ────────────────────────────────────────────────────────────────

async def close_redis_pool() -> None:
    """Close the Redis connection pool during app shutdown."""
    await redis_pool.aclose()
