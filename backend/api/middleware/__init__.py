from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from .rate_limit import rate_limit_middleware

def setup_middleware(app: FastAPI, redis: Redis):
    """Set up all middleware components"""
    
    # Add CORS middleware with proper configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:5174",
            "http://localhost:5174"
        ],  # Frontend dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    
    # Add rate limiting middleware
    app.middleware("http")(rate_limit_middleware)
    
    # Store Redis instance in app state
    app.state.redis = redis 