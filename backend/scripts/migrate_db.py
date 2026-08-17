import asyncio
from sqlalchemy import text
from app.db.session import engine

async def migrate():
    async with engine.begin() as conn:
        res = await conn.execute(text("SHOW COLUMNS FROM credentials LIKE 'owner_email'"))
        row = res.fetchone()
        if not row:
            print("Adding owner_email column to credentials table...")
            await conn.execute(text("ALTER TABLE credentials ADD COLUMN owner_email VARCHAR(255) DEFAULT 'admin@securerotate.local'"))
            print("Successfully added owner_email!")
        else:
            print("Column owner_email already exists.")

if __name__ == "__main__":
    asyncio.run(migrate())
