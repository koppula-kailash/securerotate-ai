"""
SecureRotate AI - Seed Demo Users Script
Populates database with initial Admin, DevOps, and Auditor users with secure Argon2 hashed passwords.

Demo Credentials:
- Admin:   admin@securerotate.local   (username: admin,   password: Admin123!,   role: ADMIN)
- DevOps:  devops@securerotate.local  (username: devops,  password: Devops123!,  role: DEVOPS)
- Auditor: auditor@securerotate.local (username: auditor, password: Auditor123!, role: AUDITOR)
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.auth_service import hash_password


async def seed_users():
    demo_users = [
        {
            "username": "admin",
            "email": "admin@securerotate.local",
            "password": "Admin123!",
            "role": "ADMIN",
        },
        {
            "username": "devops",
            "email": "devops@securerotate.local",
            "password": "Devops123!",
            "role": "DEVOPS",
        },
        {
            "username": "auditor",
            "email": "auditor@securerotate.local",
            "password": "Auditor123!",
            "role": "AUDITOR",
        },
    ]

    async with AsyncSessionLocal() as session:
        created_count = 0
        for udata in demo_users:
            stmt = select(User).where(
                (User.username == udata["username"]) | (User.email == udata["email"])
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                hashed = hash_password(udata["password"])
                user = User(
                    username=udata["username"],
                    email=udata["email"],
                    password_hash=hashed,
                    role=udata["role"],
                    is_active=True,
                )
                session.add(user)
                created_count += 1
                print(f"Created user '{udata['username']}' ({udata['role']})")
            else:
                existing.role = udata["role"]
                existing.is_active = True
                print(f"Updated user '{udata['username']}' role to {udata['role']}")

        await session.commit()
        print("Successfully synchronized demo users.")


if __name__ == "__main__":
    asyncio.run(seed_users())
