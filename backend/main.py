from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
import os
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import routes and middleware
from api.database import init_db
from api.routes import chat
from api.middleware.rate_limiter import RateLimitMiddleware
from api.middleware.session import SessionMiddleware

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title=os.getenv("API_TITLE", "ChatTNG API"),
        description=os.getenv("API_DESCRIPTION", "Star Trek: TNG Dialog Chat API"),
        version=os.getenv("API_VERSION", "1.0.0")
    )

    # Configure CORS
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware in correct order
    app.add_middleware(SessionMiddleware)  # Session must be before rate limiter
    app.add_middleware(RateLimitMiddleware)  # Rate limiter depends on session

    # Include routers
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

    @app.get("/health")
    async def health_check():
        """Basic health check endpoint"""
        logger.debug("Received health check request at /health")
        try:
            # Check database connection
            await init_db()
            # Return healthy response
            return {
                "status": "healthy",
                "timestamp": int(time.time()),
                "environment": os.getenv("NODE_ENV", "production")
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": int(time.time())
                }
            )

    @app.on_event("startup")
    async def startup():
        """Initialize database on startup"""
        logger.debug("Running startup event")
        await init_db()
        logger.debug("Database initialized")

    return app

app = create_app()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
            "message": str(exc)
        }
    ) 