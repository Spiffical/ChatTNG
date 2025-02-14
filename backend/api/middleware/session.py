from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import redis
import uuid
import json
from typing import Optional, Dict, Any
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        self._load_config()

    def _load_config(self):
        """Load session configuration from Redis"""
        try:
            # Get key prefixes
            prefixes_json = self.redis.get("key_prefixes")
            if not prefixes_json:
                raise ValueError("Key prefixes not found in Redis")
            self.prefixes = json.loads(prefixes_json)
            
            # Get session config
            config_json = self.redis.get("session_config")
            if not config_json:
                raise ValueError("Session config not found in Redis")
            self.config = json.loads(config_json)
            
            self.session_cookie = self.config["cookie_name"]
            self.session_expire = self.config["expiry"]
            self.cookie_secure = self.config["cookie_secure"]
            self.cookie_httponly = self.config["cookie_httponly"]
            self.cookie_samesite = self.config["cookie_samesite"]
            
        except Exception as e:
            # Fallback to default values if Redis config not available
            self.prefixes = {"session": "sess:"}
            self.session_cookie = "chattng_session"
            self.session_expire = 24 * 60 * 60  # 24 hours
            self.cookie_secure = True
            self.cookie_httponly = True
            self.cookie_samesite = "lax"
            print(f"Warning: Using default session config. Error: {str(e)}")

    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session data"""
        return f"{self.prefixes['session']}{session_id}"

    def _is_valid_session(self, session_id: str) -> bool:
        """Check if session exists and is valid"""
        key = self._get_session_key(session_id)
        return bool(self.redis.exists(key))

    def _get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data from Redis"""
        key = self._get_session_key(session_id)
        data = self.redis.get(key)
        
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return self._initialize_session_data()
        
        return self._initialize_session_data()

    def _initialize_session_data(self) -> Dict[str, Any]:
        """Initialize new session data"""
        return {
            "created_at": int(time.time()),
            "last_activity": int(time.time()),
            "conversation_history": [],
            "preferences": {}
        }

    def _save_session_data(self, session_id: str, data: Dict[str, Any]) -> None:
        """Save session data to Redis"""
        key = self._get_session_key(session_id)
        # Update last activity
        data["last_activity"] = int(time.time())
        # Save to Redis with expiry
        self.redis.setex(
            key,
            self.session_expire,
            json.dumps(data)
        )

    def _create_session_id(self) -> str:
        """Create a new session ID"""
        return str(uuid.uuid4())

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle the request and manage session"""
        
        # Get or create session
        session_id = request.cookies.get(self.session_cookie)
        is_new_session = False

        if not session_id or not self._is_valid_session(session_id):
            session_id = self._create_session_id()
            is_new_session = True

        # Get session data
        session_data = self._get_session_data(session_id)

        # Add session to request state
        request.state.session_id = session_id
        request.state.session = session_data

        # Process request
        response = await call_next(request)

        # Save session data
        self._save_session_data(session_id, session_data)

        # Set session cookie for new sessions
        if is_new_session:
            response.set_cookie(
                self.session_cookie,
                session_id,
                max_age=self.session_expire,
                httponly=self.cookie_httponly,
                secure=self.cookie_secure,
                samesite=self.cookie_samesite
            )

        return response 