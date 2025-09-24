#!/usr/bin/env python
"""Verify that strategy tables were created successfully."""
import asyncio
from sqlalchemy import text
from app.database import get_async_session


async def verify_tables():
    """Check if all strategy and tag tables exist in the database."""

    tables_to_check = [
        'strategies',
        'strategy_legs',
        'strategy_metrics',
        'strategy_tags',
        'tags_v2'
    ]

    async with get_async_session() as db:
        print("Checking database tables...")
        print("-" * 50)

        # Check if tables exist
        for table_name in tables_to_check:
            query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                );
            """)
            result = await db.execute(query, {"table_name": table_name})
            exists = result.scalar()

            status = "EXISTS" if exists else "MISSING"
            print(f"  {table_name:<20} ... {status}")

        print("-" * 50)

        # Check if strategy_id column was added to positions table
        query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'positions'
                AND column_name = 'strategy_id'
            );
        """)
        result = await db.execute(query)
        has_strategy_id = result.scalar()

        if has_strategy_id:
            print("  positions.strategy_id column ... EXISTS")
        else:
            print("  positions.strategy_id column ... MISSING")

        # Count existing positions that need strategies
        query = text("""
            SELECT COUNT(*) FROM positions
            WHERE strategy_id IS NULL
            AND deleted_at IS NULL;
        """)
        result = await db.execute(query)
        positions_without_strategy = result.scalar()

        print("-" * 50)
        print(f"\nPositions without strategies: {positions_without_strategy}")

        if positions_without_strategy > 0:
            print(f"Note: {positions_without_strategy} positions need to be wrapped in strategies")

            # Get portfolio breakdown
            query = text("""
                SELECT p.name, COUNT(pos.id) as position_count
                FROM portfolios p
                LEFT JOIN positions pos ON pos.portfolio_id = p.id
                WHERE pos.strategy_id IS NULL
                AND pos.deleted_at IS NULL
                GROUP BY p.id, p.name
                ORDER BY p.name;
            """)
            result = await db.execute(query)
            portfolios = result.fetchall()

            if portfolios:
                print("\nBreakdown by portfolio:")
                for portfolio in portfolios:
                    print(f"  - {portfolio.name}: {portfolio.position_count} positions")

        return True


if __name__ == "__main__":
    asyncio.run(verify_tables())