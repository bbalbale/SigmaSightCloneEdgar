#!/usr/bin/env python3
"""
Verify Railway database migration status
"""
import asyncio
import os
from sqlalchemy import text
from app.database import get_async_session

# Fix Railway DATABASE_URL format
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

async def verify():
    async with get_async_session() as db:
        # Check migration version
        result = await db.execute(text('SELECT version_num FROM alembic_version'))
        version = result.fetchone()[0]
        print(f'✅ Migration version: {version}')

        # Check strategy tables are gone
        result = await db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('strategies', 'strategy_legs', 'strategy_metrics', 'strategy_tags')
        """))
        count = result.fetchone()[0]
        status = "✅ REMOVED" if count == 0 else f"❌ STILL EXISTS ({count} tables)"
        print(f'Strategy tables: {status}')

        # Check positions.strategy_id column is gone
        result = await db.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'positions'
            AND column_name = 'strategy_id'
        """))
        exists = result.fetchone()[0] > 0
        status = "❌ STILL EXISTS" if exists else "✅ REMOVED"
        print(f'positions.strategy_id column: {status}')

        # Check position_tags table exists
        result = await db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'position_tags'
        """))
        exists = result.fetchone()[0] > 0
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f'position_tags table: {status}')

asyncio.run(verify())
