from fastapi import Request, HTTPException
from redis.asyncio import Redis
from datetime import datetime, timedelta
import json
from starlette.datastructures import MutableHeaders

class RateLimiter:
    def __init__(
        self,
        redis: Redis,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        self.redis = redis
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

    async def _get_window_stats(self, key: str, window_size: int) -> tuple[int, float]:
        """Get the number of requests and time until window expires"""
        now = datetime.utcnow().timestamp()
        window_start = now - window_size

        # Clean old requests
        await self.redis.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        count = await self.redis.zcount(key, window_start, float('inf'))
        
        # Get time until oldest request expires
        oldest = await self.redis.zrange(key, 0, 0, withscores=True)
        ttl = window_size - (now - oldest[0][1]) if oldest else window_size
        
        return count, ttl

    async def is_rate_limited(self, request: Request) -> tuple[bool, dict]:
        """Check if request should be rate limited"""
        client_ip = request.client.host
        
        # Get session ID from headers or use anonymous
        session_id = request.headers.get("X-Session-ID", "anonymous")
        
        # Keys for different time windows
        minute_key = f"rate_limit:1m:{client_ip}:{session_id}"
        hour_key = f"rate_limit:1h:{client_ip}:{session_id}"
        
        now = datetime.utcnow().timestamp()
        pipe = self.redis.pipeline()

        # Add request timestamp to both windows
        pipe.zadd(minute_key, {str(now): now})
        pipe.zadd(hour_key, {str(now): now})
        
        # Set expiry to prevent keys from growing indefinitely
        pipe.expire(minute_key, 60)
        pipe.expire(hour_key, 3600)
        
        await pipe.execute()

        # Check minute limit
        minute_count, minute_ttl = await self._get_window_stats(minute_key, 60)
        if minute_count > self.requests_per_minute:
            return True, {
                "window": "minute",
                "limit": self.requests_per_minute,
                "remaining": 0,
                "reset": minute_ttl
            }

        # Check hour limit
        hour_count, hour_ttl = await self._get_window_stats(hour_key, 3600)
        if hour_count > self.requests_per_hour:
            return True, {
                "window": "hour",
                "limit": self.requests_per_hour,
                "remaining": 0,
                "reset": hour_ttl
            }

        return False, {
            "window": "minute",
            "limit": self.requests_per_minute,
            "remaining": self.requests_per_minute - minute_count,
            "reset": minute_ttl
        }

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for certain paths
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)

    # Get Redis from app state
    redis = request.app.state.redis
    limiter = RateLimiter(redis)
    
    # Check rate limit
    is_limited, limit_info = await limiter.is_rate_limited(request)
    
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too many requests",
                "limit_info": limit_info
            }
        )
    
    # Add rate limit info to response headers
    response = await call_next(request)
    headers = MutableHeaders(response.headers)
    headers["X-RateLimit-Limit"] = str(limit_info["limit"])
    headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
    headers["X-RateLimit-Reset"] = str(int(limit_info["reset"]))
    
    return response 