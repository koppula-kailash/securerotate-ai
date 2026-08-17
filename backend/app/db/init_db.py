"""
SecureRotate AI - Database Initialization Module
Registers models and creates MySQL tables asynchronously using the existing engine.
Automatically seeds default demo users if users table is empty.
"""

import logging
from sqlalchemy import select
from app.db.session import engine, AsyncSessionLocal
from app.models import Base, User, Credential, Dependency, RotationApproval, AuditLog, Notification, RotationHistory
from app.services.auth_service import hash_password

logger = logging.getLogger("securerotate.db")


async def migrate_missing_columns() -> None:
    """Safely adds any missing columns such as owner_email to existing database tables."""
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            # Check credentials table columns
            res = await conn.execute(text("SHOW COLUMNS FROM credentials LIKE 'owner_email'"))
            if not res.fetchone():
                logger.info("Migrating database: adding owner_email to credentials table...")
                await conn.execute(text("ALTER TABLE credentials ADD COLUMN owner_email VARCHAR(255) DEFAULT 'admin@securerotate.local'"))
                logger.info("Column owner_email added successfully.")
    except Exception as e:
        logger.warning(f"Column migration check note: {e}")


async def seed_demo_users_if_empty() -> None:
    """Seeds Admin, DevOps, and Auditor accounts if no users exist in database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        first_user = result.scalar_one_or_none()
        if not first_user:
            logger.info("Seeding default demo users (Admin, DevOps, Auditor)...")
            demo_users = [
                {"username": "admin", "email": "admin@securerotate.local", "password": "Admin123!", "role": "ADMIN"},
                {"username": "devops", "email": "devops@securerotate.local", "password": "Devops123!", "role": "DEVOPS"},
                {"username": "auditor", "email": "auditor@securerotate.local", "password": "Auditor123!", "role": "AUDITOR"},
            ]
            for u in demo_users:
                hashed = hash_password(u["password"])
                session.add(User(
                    username=u["username"],
                    email=u["email"],
                    password_hash=hashed,
                    role=u["role"],
                    is_active=True,
                ))
            await session.commit()
            logger.info("Demo users seeded successfully.")


async def init_db() -> None:
    """
    Initializes relational database schema by creating all missing tables.
    Uses existing SQLAlchemy async engine from app.db.session.
    Does NOT drop, truncate, or overwrite existing tables or data.
    """
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
        await migrate_missing_columns()
        await seed_demo_users_if_empty()
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")
        raise

