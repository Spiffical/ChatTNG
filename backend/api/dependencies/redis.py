from redis.asyncio import Redis, ConnectionPool
import os
from typing import AsyncGenerator

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Redis pool
redis_pool = ConnectionPool.from_url(
    REDIS_URL,
    max_connections=10,
    decode_responses=True
)

async def get_redis() -> AsyncGenerator[Redis, None]:
    """Get Redis connection from pool"""
    redis = Redis(connection_pool=redis_pool)
    try:
        yield redis
    finally:
        await redis.close() 