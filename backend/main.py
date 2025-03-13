import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
import os
import logging
import time
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

# Configure logging before anything else
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Log startup information immediately
logger.info("Starting application initialization...")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Python version: {sys.version}")

try:
    # Load environment variables
    logger.info("Loading environment variables...")
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
    
    # Import routes and middleware
    logger.info("Importing application modules...")
    from api.database import init_db
    from api.routes import chat
    from api.routes import video
    from api.middleware.rate_limiter import RateLimitMiddleware
    from api.middleware.session import SessionMiddleware
    from api.middleware.health import HealthCheckMiddleware
    
    def create_app() -> FastAPI:
        """Create and configure the FastAPI application"""
        logger.info("Creating FastAPI application...")
        
        try:
            app = FastAPI(
                title=os.getenv("API_TITLE", "ChatTNG API"),
                description=os.getenv("API_DESCRIPTION", "Star Trek: TNG Dialog Chat API"),
                version=os.getenv("API_VERSION", "1.0.0"),
                docs_url=None if os.getenv("DEBUG", "false").lower() == "false" else "/docs",
                redoc_url=None if os.getenv("DEBUG", "false").lower() == "false" else "/redoc",
                openapi_url=None if os.getenv("DEBUG", "false").lower() == "false" else "/openapi.json"
            )

            # Add GZip compression
            app.add_middleware(GZipMiddleware, minimum_size=1000)

            # Add CORS middleware with proper configuration
            logger.info("Configuring CORS...")
            cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["*"],
                max_age=3600
            )

            # Add request ID middleware
            @app.middleware("http")
            async def add_request_id(request: Request, call_next):
                request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
                request.state.request_id = request_id
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response

            # Add response time middleware
            @app.middleware("http")
            async def add_response_time(request: Request, call_next):
                start_time = time.time()
                response = await call_next(request)
                process_time = time.time() - start_time
                response.headers["X-Process-Time"] = str(process_time)
                return response

            # Add error handling middleware
            @app.middleware("http")
            async def catch_exceptions(request: Request, call_next):
                try:
                    return await call_next(request)
                except Exception as e:
                    logger.exception(f"Unhandled exception: {str(e)}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "detail": "Internal server error",
                            "request_id": getattr(request.state, "request_id", None)
                        }
                    )

            # Add custom middleware in correct order
            logger.info("Adding middleware...")
            app.add_middleware(HealthCheckMiddleware)
            app.add_middleware(SessionMiddleware)
            app.add_middleware(RateLimitMiddleware)

            # Include routers
            logger.info("Including routers...")
            app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
            app.include_router(video.router, prefix="/api/video", tags=["video"])

            @app.get("/ping")
            async def ping():
                """Simple ping endpoint for basic health checks"""
                return {"status": "ok", "timestamp": int(time.time())}

            @app.get("/debug")
            async def debug():
                """Debug endpoint to check application state"""
                return {
                    "status": "ok",
                    "timestamp": int(time.time()),
                    "environment": dict(os.environ),
                    "cwd": os.getcwd(),
                    "python_path": sys.path,
                    "config_dir_contents": os.listdir(Path(__file__).parent / "config")
                }

            @app.get("/health")
            async def health_check():
                """Detailed health check endpoint"""
                response = {
                    "status": "healthy",
                    "timestamp": int(time.time()),
                    "components": {}
                }

                # Check if database URL is configured
                db_url = os.getenv("DATABASE_URL")
                if not db_url:
                    response["components"]["database"] = {
                        "status": "unconfigured",
                        "message": "Database URL not set"
                    }
                else:
                    try:
                        await init_db()
                        response["components"]["database"] = {
                            "status": "healthy",
                            "message": "Connected successfully"
                        }
                    except Exception as e:
                        logger.error(f"Database connection failed: {str(e)}", exc_info=True)
                        response["components"]["database"] = {
                            "status": "unhealthy",
                            "message": str(e)
                        }

                return response

            @app.on_event("startup")
            async def startup():
                """Initialize application on startup"""
                logger.info("Application startup event triggered")
                logger.info(f"Current directory: {os.getcwd()}")
                logger.info(f"Config directory contents: {os.listdir(Path(__file__).parent / 'config')}")
                
                # Log non-sensitive environment variables
                safe_env = {k: v for k, v in os.environ.items() 
                          if not any(secret in k.lower() 
                                   for secret in ['key', 'secret', 'password', 'token'])}
                logger.info(f"Environment variables (excluding secrets): {safe_env}")
                
                # Start background task for cleaning up expired shared conversations
                asyncio.create_task(cleanup_expired_shares())
                
            async def cleanup_expired_shares():
                """Background task to periodically clean up expired shared conversations"""
                from api.database import get_db
                from api.models.conversation import SharedConversation
                
                logger.info("Starting background task for cleaning up expired shared conversations")
                
                while True:
                    try:
                        # Sleep at the start to avoid immediate cleanup on app startup
                        # This gives the application time to fully initialize
                        await asyncio.sleep(60 * 60)  # Run every hour
                        
                        logger.info("Running cleanup of expired shared conversations")
                        # Get database session
                        db_gen = get_db()
                        db: AsyncSession = await anext(db_gen)
                        
                        try:
                            # Delete expired shared conversations
                            stmt = delete(SharedConversation).where(
                                SharedConversation.expires_at < datetime.utcnow()
                            )
                            result = await db.execute(stmt)
                            await db.commit()
                            
                            # Log the number of deleted conversations
                            deleted_count = result.rowcount
                            logger.info(f"Deleted {deleted_count} expired shared conversations")
                            
                        except Exception as e:
                            logger.error(f"Error cleaning up expired shared conversations: {str(e)}", exc_info=True)
                            await db.rollback()
                        finally:
                            await db.close()
                            
                    except Exception as e:
                        logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)
                    
                    # Sleep between cleanup runs (24 hours)
                    await asyncio.sleep(60 * 60 * 23)  # Sleep for 23 hours (total 24 hours between runs)
                    
            return app

        except Exception as e:
            logger.critical(f"Failed to create application: {str(e)}", exc_info=True)
            raise

    # Create the application
    logger.info("Creating application instance...")
    app = create_app()
    logger.info("Application instance created successfully")

except Exception as e:
    logger.critical(f"Fatal error during application initialization: {str(e)}", exc_info=True)
    raise