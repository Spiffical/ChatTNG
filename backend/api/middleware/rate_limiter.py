from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import redis
import time
import json
from typing import Optional, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        self._load_config()
        
    def _load_config(self):
        """Load rate limiting configuration from Redis"""
        try:
            # Get key prefixes
            prefixes_json = self.redis.get("key_prefixes")
            if not prefixes_json:
                raise ValueError("Key prefixes not found in Redis")
            self.prefixes = json.loads(prefixes_json)
            
            # Get rate limit config
            config_json = self.redis.get("rate_limit_config")
            if not config_json:
                raise ValueError("Rate limit config not found in Redis")
            self.config = json.loads(config_json)
            
            self.rate_limit = self.config["requests_per_minute"]
            self.window = self.config["window_size"]
            
        except Exception as e:
            # Fallback to default values if Redis config not available
            self.prefixes = {"rate_limit": "rl:"}
            self.rate_limit = 60
            self.window = 60
            print(f"Warning: Using default rate limit config. Error: {str(e)}")

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier from session or IP"""
        try:
            if hasattr(request, "session") and "session_id" in request.session:
                return request.session["session_id"]
        except Exception:
            pass
        return request.client.host if request.client else "unknown"

    def _get_rate_limit_key(self, client_id: str) -> str:
        """Generate Redis key for rate limiting"""
        return f"{self.prefixes['rate_limit']}{client_id}"

    async def _check_rate_limit(self, client_id: str) -> tuple[bool, Dict[str, Any]]:
        """Check if client has exceeded rate limit using sliding window"""
        current_time = int(time.time())
        key = self._get_rate_limit_key(client_id)
        window_start = current_time - self.window
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old requests outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Add new request
        pipe.zadd(key, {str(current_time): current_time})
        # Count requests in window
        pipe.zcard(key)
        # Set key expiry
        pipe.expire(key, self.window * 2)  # 2x window for safety
        
        # Execute pipeline
        _, _, request_count, _ = pipe.execute()
        
        # Calculate remaining requests and reset time
        remaining = max(0, self.rate_limit - request_count)
        reset_time = current_time + self.window
        
        # Return rate limit info
        rate_limit_info = {
            "limit": self.rate_limit,
            "remaining": remaining,
            "reset": reset_time,
            "window": self.window
        }
        
        return request_count <= self.rate_limit, rate_limit_info

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle the request and apply rate limiting"""
        
        # Skip rate limiting for health check
        if request.url.path == "/api/health":
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)
        
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
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])
        
        return response 