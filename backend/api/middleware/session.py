import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis
import time
import os
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url=None):
        super().__init__(app)
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.session_cookie = os.getenv("SESSION_COOKIE", "chattng_session")
        self.session_expire = int(os.getenv("SESSION_EXPIRE", "86400"))  # 24 hours
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
            logger.info("Session middleware using Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory sessions: {str(e)}")
            self.use_redis = False
            self.in_memory_sessions = {}

    async def _get_session_redis(self, session_id: str) -> Dict[str, Any]:
        """Get session data from Redis"""
        try:
            data = await self.redis.get(f"session:{session_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis session get failed: {str(e)}")
        return {}

    async def _set_session_redis(self, session_id: str, data: Dict[str, Any]):
        """Set session data in Redis"""
        try:
            await self.redis.setex(
                f"session:{session_id}",
                self.session_expire,
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Redis session set failed: {str(e)}")

    def _get_session_memory(self, session_id: str) -> Dict[str, Any]:
        """Get session data from memory"""
        if session_id in self.in_memory_sessions:
            session_data, expiry = self.in_memory_sessions[session_id]
            if expiry > time.time():
                return session_data
            del self.in_memory_sessions[session_id]
        return {}

    def _set_session_memory(self, session_id: str, data: Dict[str, Any]):
        """Set session data in memory"""
        expiry = time.time() + self.session_expire
        self.in_memory_sessions[session_id] = (data, expiry)

    async def dispatch(self, request: Request, call_next):
        # Skip session handling for health check endpoints
        if request.url.path in ["/health", "/ping", "/debug"]:
            return await call_next(request)

        # Get or create session ID
        session_id = request.cookies.get(self.session_cookie)
        
        # Get session data
        if self.use_redis:
            session_data = await self._get_session_redis(session_id) if session_id else {}
        else:
            session_data = self._get_session_memory(session_id) if session_id else {}
        
        # Attach session to request
        request.state.session = session_data
        request.state.session_id = session_id
        
        # Process request
        response = await call_next(request)
        
        # Update session if modified
        if hasattr(request.state, "session_modified") and request.state.session_modified:
            if self.use_redis:
                await self._set_session_redis(session_id, session_data)
            else:
                self._set_session_memory(session_id, session_data)
            
            # Set session cookie if needed
            if not session_id:
                response.set_cookie(
                    self.session_cookie,
                    session_id,
                    max_age=self.session_expire,
                    httponly=True,
                    samesite="lax"
                )
        
        return response 