from fastapi import FastAPI
from redis.asyncio import Redis
import os

from api.database import init_db
from api.routers import chat
from api.middleware import setup_middleware

# Create FastAPI app
app = FastAPI(title="ChatTNG API")

# Create Redis connection
redis = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    encoding="utf-8",
    decode_responses=True
)

# Set up middleware
setup_middleware(app, redis)

# Include routers
app.include_router(chat.router)

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    """Close Redis connection on shutdown"""
    await redis.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 