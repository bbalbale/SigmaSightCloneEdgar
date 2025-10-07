"""
Backfill investment_class for existing positions (Phase 8.1 Task 11a)

This script:
1. Finds all positions with NULL investment_class
2. Applies determine_investment_class() heuristic to each
3. Updates the database with correct classification

Usage:
    # Dry run (preview changes)
    uv run python scripts/backfill_investment_class.py --dry-run

    # Execute backfill
    uv run python scripts/backfill_investment_class.py --execute

    # Railway (DATABASE_URL auto-converted)
    uv run python scripts/backfill_investment_class.py --execute
"""

import asyncio
import argparse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.db.seed_demo_portfolios import determine_investment_class, determine_investment_subtype
from app.core.logging import get_logger

logger = get_logger(__name__)


async def backfill_investment_class(dry_run: bool = True):
    """
    Backfill investment_class and investment_subtype for all positions

    Args:
        dry_run: If True, only preview changes without updating database
    """
    async with AsyncSessionLocal() as db:
        try:
            # Find all positions with NULL investment_class
            stmt = select(Position).where(Position.investment_class.is_(None))
            result = await db.execute(stmt)
            positions = result.scalars().all()

            if not positions:
                logger.info("✅ No positions need backfilling. All positions already have investment_class set.")
                return

            logger.info(f"Found {len(positions)} positions with NULL investment_class")

            # Group by classification for reporting
            classification_counts = {'PUBLIC': 0, 'OPTIONS': 0, 'PRIVATE': 0}
            updates = []

            for position in positions:
                # Apply heuristic
                investment_class = determine_investment_class(position.symbol)
                investment_subtype = determine_investment_subtype(position.symbol) if investment_class == 'PRIVATE' else None

                classification_counts[investment_class] += 1

                updates.append({
                    'id': position.id,
                    'symbol': position.symbol,
                    'current_class': position.investment_class,
                    'new_class': investment_class,
                    'new_subtype': investment_subtype
                })

                if dry_run:
                    logger.info(
                        f"  [{investment_class}] {position.symbol} "
                        f"(subtype: {investment_subtype or 'N/A'})"
                    )

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("BACKFILL SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total positions to update: {len(positions)}")
            logger.info(f"  PUBLIC:  {classification_counts['PUBLIC']}")
            logger.info(f"  OPTIONS: {classification_counts['OPTIONS']}")
            logger.info(f"  PRIVATE: {classification_counts['PRIVATE']}")
            logger.info("=" * 80)

            if dry_run:
                logger.info("\n⚠️  DRY RUN - No changes made to database")
                logger.info("Run with --execute to apply changes")
                return

            # Execute updates
            logger.info("\n🔄 Executing database updates...")
            for update_data in updates:
                stmt = (
                    update(Position)
                    .where(Position.id == update_data['id'])
                    .values(
                        investment_class=update_data['new_class'],
                        investment_subtype=update_data['new_subtype']
                    )
                )
                await db.execute(stmt)

            await db.commit()
            logger.info(f"\n✅ Successfully backfilled {len(positions)} positions")

        except Exception as e:
            logger.error(f"❌ Error during backfill: {e}")
            await db.rollback()
            raise


async def verify_backfill():
    """Verify backfill results"""
    async with AsyncSessionLocal() as db:
        try:
            # Count NULL investment_class
            stmt = select(Position).where(Position.investment_class.is_(None))
            result = await db.execute(stmt)
            null_count = len(result.scalars().all())

            # Count by classification
            for classification in ['PUBLIC', 'OPTIONS', 'PRIVATE']:
                stmt = select(Position).where(Position.investment_class == classification)
                result = await db.execute(stmt)
                count = len(result.scalars().all())
                logger.info(f"{classification}: {count} positions")

            if null_count > 0:
                logger.warning(f"⚠️  {null_count} positions still have NULL investment_class")
            else:
                logger.info("✅ All positions have investment_class set")

        except Exception as e:
            logger.error(f"Error during verification: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Backfill investment_class for positions")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating database (default)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute backfill and update database'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify backfill results'
    )

    args = parser.parse_args()

    # Default to dry run if neither execute nor verify specified
    if not args.execute and not args.verify:
        args.dry_run = True

    if args.verify:
        logger.info("Verifying backfill results...")
        asyncio.run(verify_backfill())
    else:
        logger.info(f"Starting backfill (dry_run={args.dry_run})...")
        asyncio.run(backfill_investment_class(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
