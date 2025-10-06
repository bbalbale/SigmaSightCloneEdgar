#!/usr/bin/env python3
"""
Check if tags_v2 table exists in Railway Postgres
"""
import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_tags_table():
    """Check if tags_v2 table exists"""

    # Get DATABASE_URL from environment (Railway will inject this)
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not set")
        return

    # Ensure async driver
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print(f"🔌 Connecting to Railway Postgres...")
    print(f"   Database URL: {database_url.split('@')[1] if '@' in database_url else 'N/A'}")

    try:
        engine = create_async_engine(database_url)

        async with engine.connect() as conn:
            # Check if tags_v2 table exists
            result = await conn.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'tags_v2'
                """)
            )

            tables = result.fetchall()

            if tables:
                print(f"✅ tags_v2 table EXISTS in Railway Postgres")

                # Get row count
                count_result = await conn.execute(text("SELECT COUNT(*) FROM tags_v2"))
                count = count_result.scalar()
                print(f"   Rows in tags_v2: {count}")

                # Get sample data
                if count > 0:
                    sample_result = await conn.execute(
                        text("SELECT id, name, user_id, is_archived FROM tags_v2 LIMIT 5")
                    )
                    samples = sample_result.fetchall()

                    print(f"\n   Sample tags:")
                    for tag in samples:
                        print(f"      {tag[1]} (archived: {tag[3]})")
            else:
                print(f"❌ tags_v2 table DOES NOT EXIST in Railway Postgres")

            # Also check position_tags table
            result = await conn.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'position_tags'
                """)
            )

            tables = result.fetchall()

            if tables:
                print(f"\n✅ position_tags table EXISTS in Railway Postgres")

                count_result = await conn.execute(text("SELECT COUNT(*) FROM position_tags"))
                count = count_result.scalar()
                print(f"   Rows in position_tags: {count}")
            else:
                print(f"\n❌ position_tags table DOES NOT EXIST in Railway Postgres")

        await engine.dispose()

    except Exception as e:
        print(f"❌ Error checking database: {e}")


if __name__ == "__main__":
    asyncio.run(check_tags_table())
