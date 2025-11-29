"""
Backfill investment_class for existing positions

Phase 8.1 Task 11a: One-time backfill script for Railway database

This script:
1. Identifies positions with NULL investment_class
2. Applies determine_investment_class() from app.db.seed_demo_portfolios
3. Updates investment_class and investment_subtype fields
4. Reports results with position counts and classifications

IMPORTANT: Reuses classification logic from seed_demo_portfolios.py to ensure
consistency across seeding and backfill operations. Any heuristic updates should
be made in seed_demo_portfolios.py and will automatically apply here.

Usage:
    # Dry run (no changes)
    uv run python scripts/migrations/backfill_investment_class.py --dry-run

    # Apply changes
    uv run python scripts/migrations/backfill_investment_class.py --apply

    # Target specific portfolio
    uv run python scripts/migrations/backfill_investment_class.py --portfolio-id <uuid> --apply
"""
import os
import asyncio
import sys
from pathlib import Path
from typing import Dict
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fix Railway DATABASE_URL format BEFORE any app imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver\n")

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.positions import Position
from app.core.logging import get_logger
from app.db.seed_demo_portfolios import determine_investment_class, determine_investment_subtype

logger = get_logger(__name__)


async def backfill_investment_class(
    db: AsyncSession,
    portfolio_id: UUID = None,
    dry_run: bool = True
) -> Dict:
    """
    Backfill investment_class for positions with NULL values

    Args:
        db: Database session
        portfolio_id: Optional portfolio UUID to limit scope
        dry_run: If True, report changes without applying them

    Returns:
        Dictionary with statistics
    """
    # Count total positions with NULL investment_class
    count_stmt = select(func.count(Position.id)).where(
        Position.investment_class.is_(None)
    )
    if portfolio_id:
        count_stmt = count_stmt.where(Position.portfolio_id == portfolio_id)

    result = await db.execute(count_stmt)
    total_null = result.scalar() or 0

    logger.info(f"Found {total_null} positions with NULL investment_class")

    if total_null == 0:
        return {
            'total_positions_checked': 0,
            'positions_updated': 0,
            'classifications': {},
            'dry_run': dry_run
        }

    # Fetch positions with NULL investment_class
    stmt = select(Position).where(Position.investment_class.is_(None))
    if portfolio_id:
        stmt = stmt.where(Position.portfolio_id == portfolio_id)

    result = await db.execute(stmt)
    positions = result.scalars().all()

    # Track statistics
    classifications = {'PUBLIC': 0, 'PRIVATE': 0, 'OPTIONS': 0}
    subtypes = {}
    updates = []

    for position in positions:
        # Determine classification
        investment_class = determine_investment_class(position.symbol)
        classifications[investment_class] += 1

        # Determine subtype for PRIVATE positions
        investment_subtype = None
        if investment_class == 'PRIVATE':
            investment_subtype = determine_investment_subtype(position.symbol)
            subtypes[investment_subtype] = subtypes.get(investment_subtype, 0) + 1

        updates.append({
            'position_id': position.id,
            'symbol': position.symbol,
            'old_class': position.investment_class,
            'new_class': investment_class,
            'new_subtype': investment_subtype
        })

        if not dry_run:
            position.investment_class = investment_class
            position.investment_subtype = investment_subtype

    # Commit changes if not dry run
    if not dry_run:
        await db.commit()
        logger.info(f"Updated {len(updates)} positions")
    else:
        logger.info(f"Dry run: Would update {len(updates)} positions")
        await db.rollback()

    # Log sample updates
    logger.info("\n=== Classification Summary ===")
    logger.info(f"PUBLIC: {classifications['PUBLIC']}")
    logger.info(f"PRIVATE: {classifications['PRIVATE']}")
    logger.info(f"OPTIONS: {classifications['OPTIONS']}")

    if subtypes:
        logger.info("\n=== Private Investment Subtypes ===")
        for subtype, count in sorted(subtypes.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"{subtype}: {count}")

    # Show first 10 updates as examples
    logger.info("\n=== Sample Updates (first 10) ===")
    for update in updates[:10]:
        logger.info(
            f"{update['symbol']:30} -> {update['new_class']:10} "
            f"(subtype: {update['new_subtype'] or 'N/A'})"
        )

    return {
        'total_positions_checked': total_null,
        'positions_updated': len(updates) if not dry_run else 0,
        'classifications': classifications,
        'subtypes': subtypes,
        'dry_run': dry_run,
        'sample_updates': updates[:10]
    }


async def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Backfill investment_class for positions')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--apply', action='store_true', help='Apply changes to database')
    parser.add_argument('--portfolio-id', type=str, help='Target specific portfolio UUID')

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        logger.error("Must specify either --dry-run or --apply")
        return

    dry_run = args.dry_run
    portfolio_id = UUID(args.portfolio_id) if args.portfolio_id else None

    logger.info("=" * 80)
    logger.info("Investment Class Backfill Script")
    logger.info("=" * 80)
    logger.info(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLY (will update database)'}")
    if portfolio_id:
        logger.info(f"Scope: Portfolio {portfolio_id}")
    else:
        logger.info("Scope: All portfolios")
    logger.info("=" * 80)

    async with get_async_session() as db:
        results = await backfill_investment_class(db, portfolio_id, dry_run)

    logger.info("\n" + "=" * 80)
    logger.info("Backfill Complete")
    logger.info("=" * 80)
    logger.info(f"Positions checked: {results['total_positions_checked']}")
    logger.info(f"Positions updated: {results['positions_updated']}")
    logger.info(f"Mode: {'DRY RUN' if results['dry_run'] else 'APPLIED'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
