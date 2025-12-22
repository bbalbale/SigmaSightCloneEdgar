"""
Remove duplicate AI tables from Core database.

These tables should only exist in the AI database (metro), not Core (gondola).
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Core DB (gondola) - where duplicates were accidentally created
CORE_DB_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

# Tables to remove (these belong in AI DB only)
TABLES_TO_REMOVE = [
    'ai_kb_documents',
    'ai_memories',
    'ai_feedback',
]


async def remove_duplicate_tables():
    engine = create_async_engine(CORE_DB_URL)

    async with engine.begin() as conn:
        for table in TABLES_TO_REMOVE:
            # Check if table exists
            result = await conn.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                f"WHERE table_schema = 'public' AND table_name = '{table}')"
            ))
            exists = result.scalar()

            if exists:
                print(f"Dropping {table} from Core database...")
                # Drop indexes first
                await conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_scope"))
                await conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_user_id"))
                await conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_tenant_id"))
                await conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_message_id"))
                await conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_rating"))
                await conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_embedding"))
                # Drop table
                await conn.execute(text(f"DROP TABLE {table} CASCADE"))
                print(f"  [OK] Dropped {table}")
            else:
                print(f"  - {table} does not exist, skipping")

        # Verify remaining AI tables
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE 'ai_%'
            ORDER BY table_name
        """))
        remaining = [row[0] for row in result.fetchall()]
        print(f"\nRemaining AI tables in Core DB: {remaining}")

    await engine.dispose()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(remove_duplicate_tables())
