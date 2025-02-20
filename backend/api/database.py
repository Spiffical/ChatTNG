from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator
import os

# Create declarative base
Base = declarative_base()

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/chattng"
)

# Get connection parameters from environment
CONNECT_TIMEOUT = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "10"))
POOL_TIMEOUT = int(os.getenv("POSTGRES_POOL_TIMEOUT", "30"))
COMMAND_TIMEOUT = int(os.getenv("POSTGRES_COMMAND_TIMEOUT", "30"))

# Create async engine with connection parameters
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    connect_args={
        "timeout": CONNECT_TIMEOUT,
        "command_timeout": COMMAND_TIMEOUT
    },
    pool_timeout=POOL_TIMEOUT
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close() 