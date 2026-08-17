"""
SecureRotate AI - Database Session & Connection Management
Configures asynchronous SQLAlchemy engine and session factory with aiomysql driver.
"""

from typing import AsyncGenerator
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger("securerotate.db")

# Create asynchronous SQLAlchemy engine
engine = create_async_engine(
    settings.get_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for creating scoped async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """
    Executes a lightweight query (SELECT 1) to test live MySQL connectivity.
    Returns True if database is reachable, False otherwise.
    Sanitizes all exceptions to ensure database passwords/connection strings are NEVER leaked.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error("Database health check failed: connection refused or unreachable.")
        return False
