"""
Restore sector tags for all portfolios

This script uses the sector_tag_service to:
1. Remove existing sector tags
2. Re-apply sector tags based on current company profile data
3. Create new tags as needed
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.services.sector_tag_service import restore_sector_tags_for_portfolio
from app.core.logging import get_logger

logger = get_logger(__name__)


async def restore_all_sector_tags():
    """Restore sector tags for all portfolios"""
    logger.info("Starting sector tag restoration for all portfolios")

    async with AsyncSessionLocal() as db:
        # Get all active portfolios
        portfolios_result = await db.execute(
            select(Portfolio).where(Portfolio.deleted_at.is_(None))
        )
        portfolios = portfolios_result.scalars().all()

        logger.info(f"Found {len(portfolios)} active portfolios")

        total_positions_tagged = 0
        total_positions_skipped = 0
        total_tags_created = 0
        portfolios_processed = 0

        for portfolio in portfolios:
            print(f"\nProcessing portfolio: {portfolio.name}")

            try:
                result = await restore_sector_tags_for_portfolio(
                    db=db,
                    portfolio_id=portfolio.id,
                    user_id=portfolio.user_id
                )

                total_positions_tagged += result.get('positions_tagged', 0)
                total_positions_skipped += result.get('positions_skipped', 0)
                total_tags_created += result.get('tags_created', 0)
                portfolios_processed += 1

                print(f"  Positions tagged: {result.get('positions_tagged', 0)}")
                print(f"  Tags created: {result.get('tags_created', 0)}")

                # Show which tags were applied
                tags_applied = result.get('tags_applied', [])
                if tags_applied:
                    print(f"  Tags applied:")
                    for tag_info in tags_applied[:10]:  # Show first 10
                        print(f"    - {tag_info['tag_name']}: {tag_info['position_count']} positions")

            except Exception as e:
                logger.error(f"Error restoring sector tags for portfolio {portfolio.name}: {e}")
                print(f"  [ERROR] Failed: {e}")
                continue

        print("\n" + "=" * 60)
        print("SECTOR TAG RESTORATION COMPLETE")
        print("=" * 60)
        print(f"\nResults:")
        print(f"  Portfolios processed: {portfolios_processed}/{len(portfolios)}")
        print(f"  Total positions tagged: {total_positions_tagged}")
        print(f"  Total positions skipped: {total_positions_skipped}")
        print(f"  Total tags created: {total_tags_created}")

        return {
            'success': True,
            'portfolios_processed': portfolios_processed,
            'positions_tagged': total_positions_tagged,
            'positions_skipped': total_positions_skipped,
            'tags_created': total_tags_created
        }


async def main():
    """Run sector tag restoration"""
    print("=" * 60)
    print("SECTOR TAG RESTORATION")
    print("=" * 60)

    await restore_all_sector_tags()

    print("\nNext step: Verify sector tags in database")
    print("  python scripts/verification/test_sector_tagging.py")


if __name__ == "__main__":
    asyncio.run(main())
