import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from redis.asyncio import Redis
import time
import json
from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url=None):
        super().__init__(app)
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self.window = 60  # 1 minute window
        self._setup_redis()

    def _setup_redis(self):
        """Setup Redis connection with fallback to in-memory tracking"""
        try:
            # Check if Redis is explicitly disabled
            redis_enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"
            if not redis_enabled:
                logger.info("Redis explicitly disabled by REDIS_ENABLED environment variable")
                raise ValueError("Redis disabled via configuration")
                
            if not self.redis_url:
                raise ValueError("Redis URL not configured")
                
            # Check if Redis URL contains placeholder
            if "{" in self.redis_url or "}" in self.redis_url:
                logger.warning(f"Redis URL contains placeholder: {self.redis_url}")
                raise ValueError("Redis URL contains placeholder values")
                
            self.redis = Redis.from_url(self.redis_url)
            self.use_redis = True
            logger.info("Rate limiter using Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory rate limiting: {str(e)}")
            self.use_redis = False
            self.in_memory_limits = {}

    async def _check_rate_limit_redis(self, client_id: str):
        """Check rate limit using Redis"""
        current = int(time.time())
        window_start = current - self.window
        
        pipe = await self.redis.pipeline()
        await pipe.zremrangebyscore(f"requests:{client_id}", 0, window_start)
        await pipe.zadd(f"requests:{client_id}", {str(current): current})
        await pipe.zcard(f"requests:{client_id}")
        await pipe.expire(f"requests:{client_id}", self.window)
        
        try:
            _, _, request_count, _ = await pipe.execute()
            allowed = request_count <= self.rate_limit
            return allowed, {"remaining": self.rate_limit - request_count, "reset": self.window}
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {str(e)}")
            return True, {"remaining": self.rate_limit, "reset": self.window}

    def _check_rate_limit_memory(self, client_id: str):
        """Check rate limit using in-memory storage"""
        current = int(time.time())
        window_start = current - self.window
        
        # Clean old entries
        if client_id in self.in_memory_limits:
            self.in_memory_limits[client_id] = [
                ts for ts in self.in_memory_limits[client_id] 
                if ts > window_start
            ]
        else:
            self.in_memory_limits[client_id] = []
        
        # Add current request
        self.in_memory_limits[client_id].append(current)
        request_count = len(self.in_memory_limits[client_id])
        
        allowed = request_count <= self.rate_limit
        return allowed, {"remaining": self.rate_limit - request_count, "reset": self.window}

    async def _check_rate_limit(self, client_id: str):
        """Check rate limit using either Redis or in-memory storage"""
        if self.use_redis:
            return await self._check_rate_limit_redis(client_id)
        return self._check_rate_limit_memory(client_id)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle the request and apply rate limiting"""
        
        # Skip rate limiting for health check
        if request.url.path in ["/health", "/ping", "/debug"]:
            return await call_next(request)

        # Get client identifier
        client_id = request.client.host
        
        # Check rate limit
        allowed, rate_limit_info = await self._check_rate_limit(client_id)
        
        if not allowed:
            # Calculate retry after time
            retry_after = rate_limit_info["reset"] - int(time.time())
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests",
                    "retry_after": retry_after,
                    "rate_limit_info": rate_limit_info
                }
            )

        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])
        
        return response 