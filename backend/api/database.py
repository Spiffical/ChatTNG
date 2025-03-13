from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects import postgresql
from typing import AsyncGenerator, Tuple
import os
import logging
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

def get_db_url() -> Tuple[str, str]:
    """
    Get and process database URLs for both async and sync operations.
    Returns a tuple of (async_url, sync_url)
    """
    # Get database URL from environment
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/chattng"
    )
    
    # Parse the URL to handle any format
    parsed = urlparse(db_url)
    
    # Create base URL without scheme
    base = f"{parsed.netloc}{parsed.path}"
    if parsed.query:
        base = f"{base}?{parsed.query}"
    
    # Create async URL (for SQLAlchemy)
    async_url = f"postgresql+asyncpg://{base}"
    
    # Create sync URL (for health checks)
    sync_url = f"postgresql://{base}"
    
    logger.info(f"Async database URL: {async_url}")
    logger.info(f"Sync database URL: {sync_url}")
    
    return async_url, sync_url

# Get database URLs
ASYNC_DATABASE_URL, SYNC_DATABASE_URL = get_db_url()

# Add debug logging
logger.info(f"Using async URL: {ASYNC_DATABASE_URL}")
try:
    import asyncpg
    logger.info("asyncpg imported successfully")
except ImportError:
    logger.error("asyncpg import failed")

# Get connection parameters from environment
CONNECT_TIMEOUT = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "30"))
POOL_TIMEOUT = int(os.getenv("POSTGRES_POOL_TIMEOUT", "60"))
COMMAND_TIMEOUT = int(os.getenv("POSTGRES_COMMAND_TIMEOUT", "60"))
POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", "30"))

logger.info("Creating async engine with the following parameters:")
logger.info(f"Database URL: {ASYNC_DATABASE_URL}")
logger.info(f"Connect timeout: {CONNECT_TIMEOUT}")
logger.info(f"Pool timeout: {POOL_TIMEOUT}")
logger.info(f"Command timeout: {COMMAND_TIMEOUT}")
logger.info(f"Pool size: {POOL_SIZE}")
logger.info(f"Max overflow: {MAX_OVERFLOW}")

# Create async engine with optimized connection parameters
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,  # Set to False in production
    future=True,
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={
        "timeout": CONNECT_TIMEOUT,
        "command_timeout": COMMAND_TIMEOUT,
        "server_settings": {
            "application_name": "chattng",
            "statement_timeout": "60000",  # 60 seconds
            "idle_in_transaction_session_timeout": "60000"  # 60 seconds
        }
    }
)

# Create async session factory with optimized settings
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False  # Disable autoflush for better performance
)

async def init_db():
    """Initialize database tables"""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with error handling"""
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()

# Alias get_session as get_db for backward compatibility
get_db = get_session 