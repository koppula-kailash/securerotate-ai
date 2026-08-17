"""
SecureRotate AI - Database Session & Connection Management
Configures asynchronous SQLAlchemy engine and session factory with aiomysql driver.

Supports:
- Local MySQL development without SSL
- Remote MySQL deployments requiring SSL (e.g. Aiven)
"""

from typing import AsyncGenerator
import logging
import os
import ssl

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger("securerotate.db")


# ---------------------------------------------------------
# Database SSL Configuration
# ---------------------------------------------------------
# Local development:
#   DB_SSL=false
#
# Aiven/remote deployment:
#   DB_SSL=true
#
# If MYSQL_SSL_CA is provided, it is used as the CA
# certificate. Otherwise Python's default trusted CA store
# is used.
# ---------------------------------------------------------

connect_args = {}

db_ssl_enabled = os.getenv("DB_SSL", "false").lower() == "true"

if db_ssl_enabled:
    ca_file = os.getenv("MYSQL_SSL_CA")

    if ca_file:
        ssl_context = ssl.create_default_context(cafile=ca_file)
    else:
        ssl_context = ssl.create_default_context()

    connect_args["ssl"] = ssl_context


# ---------------------------------------------------------
# Create asynchronous SQLAlchemy engine
# ---------------------------------------------------------

engine = create_async_engine(
    settings.get_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args,
)


# ---------------------------------------------------------
# Async session factory
# ---------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------------------------------------------------------
# FastAPI database dependency
# ---------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for creating scoped async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------
# Database health check
# ---------------------------------------------------------

async def check_database_connection() -> bool:
    """
    Executes a lightweight query (SELECT 1) to test live MySQL
    connectivity.

    Returns:
        True  - database is reachable
        False - database is unavailable

    Database credentials and connection strings are never
    included in error messages.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1

    except Exception:
        logger.error(
            "Database health check failed: "
            "connection refused or unreachable."
        )
        return False