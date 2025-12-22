"""Check both Railway databases for AI tables."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Core DB (gondola)
CORE_DB_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

# AI DB (metro) - from the migration script references
AI_DB_URL = "postgresql+asyncpg://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway"


async def check_db(name: str, url: str):
    print(f"\n{'='*60}")
    print(f"Checking {name} database...")
    print(f"{'='*60}")

    try:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            # Check for AI tables
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name LIKE 'ai_%'
                ORDER BY table_name
            """))
            ai_tables = [row[0] for row in result.fetchall()]
            print(f"AI tables found: {ai_tables if ai_tables else 'NONE'}")

            # Check for pgvector
            result = await conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            ))
            has_pgvector = result.scalar()
            print(f"pgvector extension: {'YES' if has_pgvector else 'NO'}")

            # Check alembic version
            try:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                versions = [row[0] for row in result.fetchall()]
                print(f"Alembic version: {versions}")
            except Exception:
                print("Alembic version: NOT FOUND")

        await engine.dispose()
    except Exception as e:
        print(f"ERROR connecting: {e}")


async def main():
    await check_db("CORE (gondola)", CORE_DB_URL)
    await check_db("AI (metro)", AI_DB_URL)


if __name__ == "__main__":
    asyncio.run(main())
