#!/usr/bin/env python
"""
Verify that migrations have been applied and tables exist.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from sqlalchemy import text
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_migrations():
    """Verify migrations have been applied."""
    async with AsyncSessionLocal() as db:
        logger.info("="*60)
        logger.info("VERIFYING DATABASE MIGRATIONS")
        logger.info("="*60)

        # Check alembic version
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        logger.info(f"\n✅ Current Alembic version: {version}")

        # Check if positions table has investment_class column
        result = await db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'positions'
            AND column_name IN ('investment_class', 'investment_subtype')
            ORDER BY column_name
        """))
        columns = result.fetchall()

        if columns:
            logger.info("\n✅ Investment classification columns exist:")
            for col in columns:
                logger.info(f"  - {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")
        else:
            logger.error("❌ Investment classification columns NOT found")

        # Check if portfolio_target_prices table exists
        result = await db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'portfolio_target_prices'
        """))
        table = result.fetchone()

        if table:
            logger.info("\n✅ portfolio_target_prices table exists")

            # Get column count
            result = await db.execute(text("""
                SELECT COUNT(*) as col_count
                FROM information_schema.columns
                WHERE table_name = 'portfolio_target_prices'
            """))
            col_count = result.scalar()
            logger.info(f"  - Has {col_count} columns")

            # Check for important columns
            result = await db.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'portfolio_target_prices'
                AND column_name IN (
                    'id', 'portfolio_id', 'symbol', 'position_type',
                    'target_price_eoy', 'target_price_next_year',
                    'expected_return_eoy', 'current_price'
                )
                ORDER BY column_name
            """))
            important_cols = result.fetchall()
            logger.info(f"  - Key columns present: {len(important_cols)}")
            for col in important_cols[:5]:
                logger.info(f"    • {col.column_name}")

            # Check for unique constraint
            result = await db.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'portfolio_target_prices'
                AND constraint_type = 'UNIQUE'
            """))
            constraints = result.fetchall()
            if constraints:
                logger.info(f"  - Unique constraints: {[c.constraint_name for c in constraints]}")

        else:
            logger.error("❌ portfolio_target_prices table NOT found")

        logger.info("\n" + "="*60)
        logger.info("Migration verification complete!")
        logger.info("="*60)


async def main():
    """Main function."""
    await verify_migrations()


if __name__ == "__main__":
    asyncio.run(main())