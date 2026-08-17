"""
SecureRotate AI - Enterprise Seed Data Generator
Populates the database with the exact 24-database enterprise scenario:
- 18 Healthy
- 3 Warning (Customer DB, Analytics DB, Order Processing DB)
- 2 Critical (Payment DB with 7 dependencies, Billing DB)
- 1 Expired (Legacy Warehouse DB)
"""

import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.session import AsyncSessionLocal
from app.db.init_db import init_db
from app.api.v1.credentials import seed_demo_data


async def main():
    print("==================================================")
    print(" SecureRotate AI - Seeding 24 Enterprise Databases")
    print("==================================================")
    print("1. Initializing schema tables...")
    await init_db()

    print("2. Seeding enterprise demo credentials & dependencies...")
    async with AsyncSessionLocal() as session:
        result = await seed_demo_data(force=True, db=session)
        print(f"Status: {result.get('message')}")
        print(f"Credentials Count: {result.get('credentials_count')}")
        print(f"Breakdown: {result.get('breakdown')}")

    print("==================================================")
    print(" Demo environment seeded successfully!")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
