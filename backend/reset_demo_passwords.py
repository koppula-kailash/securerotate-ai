import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.auth_service import hash_password


DEMO_USERS = {
    "admin": "Admin123!",
    "devops": "Devops123!",
    "auditor": "Auditor123!",
}


async def reset_demo_passwords():
    async with AsyncSessionLocal() as session:
        for username, password in DEMO_USERS.items():
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()

            if user is None:
                print(f"[ERROR] User not found: {username}")
                continue

            user.password_hash = hash_password(password)

            print(f"[OK] Password reset: {username}")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(reset_demo_passwords())