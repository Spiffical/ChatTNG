from redis.asyncio import Redis, ConnectionPool
import os
from typing import AsyncGenerator, Optional
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Check if Redis is enabled
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Redis pool if enabled
redis_pool = None
if REDIS_ENABLED:
    try:
        # Check if Redis URL contains placeholder
        if "{" in REDIS_URL or "}" in REDIS_URL:
            logger.warning(f"Redis URL contains placeholder: {REDIS_URL}")
            raise ValueError("Redis URL contains placeholder values")
            
        redis_pool = ConnectionPool.from_url(
            REDIS_URL,
            max_connections=10,
            decode_responses=True
        )
        logger.info(f"Redis pool initialized with URL: {REDIS_URL}")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis pool: {str(e)}")
else:
    logger.info("Redis disabled by configuration")

async def get_redis() -> AsyncGenerator[Optional[Redis], None]:
    """Get Redis connection from pool if Redis is enabled"""
    if not REDIS_ENABLED or redis_pool is None:
        logger.debug("Redis disabled or unavailable, yielding None")
        yield None
        return
        
    redis = Redis(connection_pool=redis_pool)
    try:
        yield redis
    finally:
        await redis.close() 