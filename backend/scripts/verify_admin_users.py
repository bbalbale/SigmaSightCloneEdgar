"""Verify admin users were created."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

async def verify():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT email, full_name, role, is_active FROM admin_users"))
        rows = result.fetchall()
        print("Admin Users in Database:")
        print("-" * 60)
        for row in rows:
            print(f"  Email: {row[0]}")
            print(f"  Name: {row[1]}")
            print(f"  Role: {row[2]}")
            print(f"  Active: {row[3]}")
            print("-" * 60)
        print(f"\nTotal: {len(rows)} admin user(s)")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify())
