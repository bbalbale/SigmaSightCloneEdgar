"""
Pre-Migration Dedupe Script for Portfolio Snapshots

This script MUST be run BEFORE applying the unique constraint migration (Task 2.10.1).
If duplicate snapshots exist when the migration runs, it will fail.

Purpose:
- Find all duplicate (portfolio_id, snapshot_date) pairs
- For each duplicate group, keep the "best" row:
  - Prefer rows where all calculations are complete (non-zero values)
  - If equal, prefer latest created_at timestamp
- Delete all other rows in the group
- Log all deletions for audit trail

Usage:
  python scripts/repair/dedupe_snapshots_pre_migration.py [--dry-run]

  --dry-run: Show what would be deleted without actually deleting
"""
import asyncio
import sys
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports (works from any checkout location)
# scripts/repair/dedupe_snapshots_pre_migration.py -> backend/
backend_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(backend_root))

from app.database import AsyncSessionLocal
from app.models.snapshots import PortfolioSnapshot
from app.core.logging import get_logger

logger = get_logger(__name__)


async def find_duplicate_groups(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Find all (portfolio_id, snapshot_date) pairs that have duplicates.

    Returns:
        List of dicts with {portfolio_id, snapshot_date, count}
    """
    # SQL query to find duplicates
    query = select(
        PortfolioSnapshot.portfolio_id,
        PortfolioSnapshot.snapshot_date,
        func.count(PortfolioSnapshot.id).label('count')
    ).group_by(
        PortfolioSnapshot.portfolio_id,
        PortfolioSnapshot.snapshot_date
    ).having(
        func.count(PortfolioSnapshot.id) > 1
    )

    result = await db.execute(query)
    duplicates = []

    for row in result:
        duplicates.append({
            'portfolio_id': row.portfolio_id,
            'snapshot_date': row.snapshot_date,
            'count': row.count
        })

    return duplicates


async def get_best_snapshot(
    db: AsyncSession,
    portfolio_id,
    snapshot_date
) -> PortfolioSnapshot:
    """
    Get the "best" snapshot from a duplicate group.

    Logic:
    1. Prefer complete snapshots (is_complete=True) over incomplete placeholders
    2. If equal, prefer snapshots with non-zero net_asset_value (complete calculations)
    3. If equal, prefer latest created_at timestamp

    Returns:
        The snapshot to keep
    """
    query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == snapshot_date
        )
    ).order_by(
        # CRITICAL: Prefer complete snapshots first (Phase 2.10 idempotency)
        # This prevents deleting real $0 NAV snapshots in favor of incomplete placeholders
        PortfolioSnapshot.is_complete.desc(),
        PortfolioSnapshot.net_asset_value.desc(),
        PortfolioSnapshot.created_at.desc()
    )

    result = await db.execute(query)
    snapshots = result.scalars().all()

    if not snapshots:
        raise ValueError(f"No snapshots found for portfolio {portfolio_id} on {snapshot_date}")

    return snapshots[0]  # First one is the "best"


async def dedupe_snapshots(dry_run: bool = False) -> Dict[str, Any]:
    """
    Main deduplication logic.

    Args:
        dry_run: If True, only show what would be deleted

    Returns:
        Summary dict with counts
    """
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting snapshot deduplication...")

            # Step 1: Find all duplicate groups
            duplicate_groups = await find_duplicate_groups(db)

            if not duplicate_groups:
                logger.info("✅ No duplicate snapshots found!")
                return {
                    'duplicate_groups': 0,
                    'snapshots_deleted': 0,
                    'snapshots_kept': 0
                }

            logger.warning(f"⚠️  Found {len(duplicate_groups)} duplicate groups")

            total_deleted = 0
            total_kept = 0
            audit_log = []

            # Step 2: Process each duplicate group
            for group in duplicate_groups:
                portfolio_id = group['portfolio_id']
                snapshot_date = group['snapshot_date']
                count = group['count']

                logger.info(
                    f"Processing portfolio {portfolio_id}, date {snapshot_date} "
                    f"({count} duplicates)"
                )

                # Step 2a: Get the "best" snapshot to keep
                best_snapshot = await get_best_snapshot(db, portfolio_id, snapshot_date)

                # Step 2b: Delete all others
                delete_query = delete(PortfolioSnapshot).where(
                    and_(
                        PortfolioSnapshot.portfolio_id == portfolio_id,
                        PortfolioSnapshot.snapshot_date == snapshot_date,
                        PortfolioSnapshot.id != best_snapshot.id  # Keep the best one
                    )
                )

                if dry_run:
                    # In dry run, just log what would be deleted
                    others_query = select(PortfolioSnapshot).where(
                        and_(
                            PortfolioSnapshot.portfolio_id == portfolio_id,
                            PortfolioSnapshot.snapshot_date == snapshot_date,
                            PortfolioSnapshot.id != best_snapshot.id
                        )
                    )
                    result = await db.execute(others_query)
                    others = result.scalars().all()

                    logger.info(f"  [DRY RUN] Would keep: {best_snapshot.id}")
                    for other in others:
                        logger.info(
                            f"  [DRY RUN] Would delete: {other.id} "
                            f"(NAV: ${other.net_asset_value:,.2f}, "
                            f"created: {other.created_at})"
                        )

                    total_deleted += len(others)
                    total_kept += 1
                else:
                    # Actually delete
                    result = await db.execute(delete_query)
                    deleted_count = result.rowcount

                    logger.info(
                        f"  Kept: {best_snapshot.id} "
                        f"(NAV: ${best_snapshot.net_asset_value:,.2f}, "
                        f"created: {best_snapshot.created_at})"
                    )
                    logger.info(f"  Deleted: {deleted_count} duplicate(s)")

                    total_deleted += deleted_count
                    total_kept += 1

                    # Audit log
                    audit_log.append({
                        'portfolio_id': str(portfolio_id),
                        'snapshot_date': snapshot_date.isoformat(),
                        'kept_id': str(best_snapshot.id),
                        'deleted_count': deleted_count,
                        'timestamp': datetime.utcnow().isoformat()
                    })

            # Step 3: Commit if not dry run
            if not dry_run:
                await db.commit()
                logger.info("✅ Changes committed to database")
            else:
                logger.info("✅ Dry run complete (no changes made)")

            # Step 4: Verify no duplicates remain (only if not dry run)
            if not dry_run:
                remaining_duplicates = await find_duplicate_groups(db)
                if remaining_duplicates:
                    logger.error(
                        f"❌ ERROR: {len(remaining_duplicates)} duplicate groups still exist!"
                    )
                    raise Exception("Deduplication failed - duplicates still exist")
                else:
                    logger.info("✅ Verified: No duplicates remain")

            return {
                'duplicate_groups': len(duplicate_groups),
                'snapshots_deleted': total_deleted,
                'snapshots_kept': total_kept,
                'audit_log': audit_log,
                'dry_run': dry_run
            }

        except Exception as e:
            logger.error(f"Error during deduplication: {e}", exc_info=True)
            await db.rollback()
            raise


async def main():
    """Main entry point"""
    # Check for --dry-run flag
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 80 + "\n")
    else:
        print("\n" + "=" * 80)
        print("⚠️  LIVE MODE - Database will be modified")
        print("=" * 80)
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
        print()

    try:
        result = await dedupe_snapshots(dry_run=dry_run)

        print("\n" + "=" * 80)
        print("DEDUPLICATION SUMMARY")
        print("=" * 80)
        print(f"Duplicate groups found: {result['duplicate_groups']}")
        print(f"Snapshots kept:         {result['snapshots_kept']}")
        print(f"Snapshots deleted:      {result['snapshots_deleted']}")
        print(f"Mode:                   {'DRY RUN' if dry_run else 'LIVE'}")
        print("=" * 80)

        if not dry_run and result['duplicate_groups'] > 0:
            print("\n✅ Deduplication complete!")
            print(f"Audit log contains {len(result['audit_log'])} entries")

            print("\n📋 Next steps:")
            print("1. Verify the results above")
            print("2. Run this SQL to confirm no duplicates:")
            print("   SELECT portfolio_id, snapshot_date, COUNT(*)")
            print("   FROM portfolio_snapshots")
            print("   GROUP BY portfolio_id, snapshot_date")
            print("   HAVING COUNT(*) > 1;")
            print("   (Should return 0 rows)")
            print("3. Proceed with migration (Task 2.10.1)")
        elif dry_run:
            print("\n📋 To run for real:")
            print("   python scripts/repair/dedupe_snapshots_pre_migration.py")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
