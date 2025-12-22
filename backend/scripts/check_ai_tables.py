"""Check AI tables and migration status on Railway."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check():
    engine = create_async_engine(
        'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'
    )
    async with engine.connect() as conn:
        # Check migration version
        result = await conn.execute(text('SELECT version_num FROM alembic_version'))
        versions = [row[0] for row in result.fetchall()]
        print('Current migration versions:', versions)

        # Check if ai_kb_documents table exists
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE 'ai_%'
        """))
        tables = [row[0] for row in result.fetchall()]
        print('AI tables found:', tables)

        # Check all tables
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        all_tables = [row[0] for row in result.fetchall()]
        print('\nAll tables:')
        for t in all_tables:
            print(f'  - {t}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(check())
