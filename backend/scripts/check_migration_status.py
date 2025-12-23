"""Quick check of Railway migration status."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set DATABASE_URL before imports
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'

async def check():
    from sqlalchemy import text
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Check alembic version
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        versions = result.fetchall()
        print(f"Alembic versions: {versions}")

        # Check if admin_users exists
        result = await db.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'admin_users'
        """))
        tables = result.fetchall()
        print(f"admin_users table exists: {len(tables) > 0}")

        # Check admin_users count if exists
        if tables:
            result = await db.execute(text("SELECT COUNT(*) FROM admin_users"))
            count = result.scalar()
            print(f"admin_users row count: {count}")

if __name__ == '__main__':
    asyncio.run(check())
