from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

# Load environment variables from root .env
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

# Import routes and middleware
from api.routes import chat
from api.middleware.rate_limiter import RateLimitMiddleware
from api.middleware.session import SessionMiddleware
from api.middleware.health import HealthCheckMiddleware

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title=os.getenv("API_TITLE", "ChatTNG API"),
        description=os.getenv("API_DESCRIPTION", "Star Trek: TNG Dialog Chat API"),
        version=os.getenv("API_VERSION", "1.0.0")
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "*"  # Allow all origins in development
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware in correct order
    app.add_middleware(HealthCheckMiddleware)  # Health check should be first
    app.add_middleware(SessionMiddleware)  # Session must be before rate limiter
    app.add_middleware(RateLimitMiddleware)  # Rate limiter depends on session

    # Include routers
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

    return app

app = create_app()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
            "message": str(exc)  # Add error message for debugging
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 