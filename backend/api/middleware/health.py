from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse
from typing import Dict, Any
import time
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg
import logging
import json
from api.database import SYNC_DATABASE_URL

# Load environment variables
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

# Configure logging
logger = logging.getLogger(__name__)

class HealthCheckMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger(__name__)
        self.last_check = 0
        self.check_interval = 60  # Check every minute
        self.health_status = self._initialize_health_status()
        
    def _initialize_health_status(self) -> Dict[str, Any]:
        """Initialize health status for all components"""
        self.logger.debug("Initializing health status for components")
        return {
            "postgres": {"status": "unknown", "last_check": 0}
        }
        
    async def _check_postgres(self) -> Dict[str, Any]:
        """Check PostgreSQL connection"""
        self.logger.debug("Checking PostgreSQL connection...")
        try:
            # Use sync URL for health checks
            conn = psycopg.connect(
                SYNC_DATABASE_URL,
                connect_timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "10")),
                autocommit=True
            )
            
            # Execute simple query to verify connection
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            
            conn.close()
            
            self.logger.debug("PostgreSQL connection successful")
            return {
                "status": "healthy",
                "last_check": int(time.time()),
                "message": "Connection successful"
            }
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {str(e)}")
            return {
                "status": "unhealthy",
                "last_check": int(time.time()),
                "error": str(e),
                "message": "Connection failed"
            }
            
    async def _update_health_status(self):
        """Update health status for critical components"""
        self.logger.debug("Updating health status...")
        current_time = int(time.time())
        
        # Only check if interval has passed
        if current_time - self.last_check < self.check_interval:
            self.logger.debug("Skipping health check - interval not passed")
            return
            
        self.health_status["postgres"] = await self._check_postgres()
        
        self.last_check = current_time
        self.logger.debug(f"Health status updated: {self.health_status}")
        
    def _get_overall_status(self) -> str:
        """Get overall system health status"""
        self.logger.debug("Getting overall status...")
        
        # Check critical components
        if self.health_status["postgres"]["status"] == "unhealthy":
            self.logger.debug("Overall status: unhealthy (PostgreSQL unhealthy)")
            return "unhealthy"
        if self.health_status["postgres"]["status"] == "unknown":
            self.logger.debug("Overall status: unknown (PostgreSQL status unknown)")
            return "unknown"
            
        self.logger.debug("Overall status: healthy")
        return "healthy"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle incoming requests and update health status"""
        await self._update_health_status()
        return await call_next(request) 