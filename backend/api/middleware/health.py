from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse
import redis
import json
from typing import Dict, Any
import time
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import pinecone
import boto3
import logging

# Load environment variables
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

class HealthCheckMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        self.last_check = 0
        self.check_interval = 60  # Check every minute
        self.health_status = self._initialize_health_status()
        
    def _initialize_health_status(self) -> Dict[str, Any]:
        """Initialize health status for all components"""
        self.logger.debug("Initializing health status for components")
        return {
            "redis": {"status": "unknown", "last_check": 0},
            "postgres": {"status": "unknown", "last_check": 0},
            "pinecone": {"status": "unknown", "last_check": 0},
            "s3": {"status": "unknown", "last_check": 0}
        }
        
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connection"""
        try:
            self.redis.ping()
            return {"status": "healthy", "last_check": int(time.time())}
        except Exception as e:
            return {
                "status": "unhealthy",
                "last_check": int(time.time()),
                "error": str(e)
            }
            
    async def _check_postgres(self) -> Dict[str, Any]:
        """Check PostgreSQL connection"""
        self.logger.debug("Checking PostgreSQL connection...")
        try:
            conn = psycopg2.connect(
                os.getenv("DATABASE_URL").replace("+asyncpg", "")
            )
            conn.close()
            self.logger.debug("PostgreSQL connection successful")
            return {"status": "healthy", "last_check": int(time.time())}
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {str(e)}")
            return {
                "status": "unhealthy",
                "last_check": int(time.time()),
                "error": str(e)
            }
            
    async def _check_pinecone(self) -> Dict[str, Any]:
        """Check Pinecone connection"""
        try:
            pinecone.init(
                api_key=os.getenv("PINECONE_API_KEY"),
                environment=os.getenv("PINECONE_ENVIRONMENT")
            )
            # Just list indexes to verify connection
            pinecone.list_indexes()
            return {"status": "healthy", "last_check": int(time.time())}
        except Exception as e:
            return {
                "status": "unhealthy",
                "last_check": int(time.time()),
                "error": str(e)
            }
            
    async def _check_s3(self) -> Dict[str, Any]:
        """Check S3 connection"""
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION")
            )
            # List buckets to verify connection
            s3.list_buckets()
            return {"status": "healthy", "last_check": int(time.time())}
        except Exception as e:
            return {
                "status": "unhealthy",
                "last_check": int(time.time()),
                "error": str(e)
            }
            
    async def _update_health_status(self):
        """Update health status for all components"""
        self.logger.debug("Updating health status...")
        current_time = int(time.time())
        
        # Only check if interval has passed
        if current_time - self.last_check < self.check_interval:
            self.logger.debug("Skipping health check - interval not passed")
            return
            
        self.health_status["redis"] = await self._check_redis()
        self.health_status["postgres"] = await self._check_postgres()
        self.health_status["pinecone"] = await self._check_pinecone()
        self.health_status["s3"] = await self._check_s3()
        
        self.last_check = current_time
        self.logger.debug(f"Health status updated: {self.health_status}")
        
    def _get_overall_status(self) -> str:
        """Get overall system health status"""
        self.logger.debug("Getting overall status...")
        if any(v["status"] == "unhealthy" for v in self.health_status.values()):
            self.logger.debug("Overall status: unhealthy")
            return "unhealthy"
        if any(v["status"] == "unknown" for v in self.health_status.values()):
            self.logger.debug("Overall status: unknown")
            return "unknown"
        self.logger.debug("Overall status: healthy")
        return "healthy"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Handle the request and check health status"""
        
        self.logger.debug(f"Received request to {request.url.path}")
        
        # Update health status periodically
        await self._update_health_status()
        
        # Return health check response for health endpoints
        if request.url.path in ["/health", "/api/health"]:
            self.logger.debug("Processing health check request")
            response_data = {
                "status": self._get_overall_status(),
                "components": self.health_status,
                "timestamp": int(time.time())
            }
            self.logger.debug(f"Health check response: {response_data}")
            return JSONResponse(response_data)
            
        # Add health status to request state
        request.state.health_status = self.health_status
        
        # Process request
        response = await call_next(request)
        return response 