"""
Sync company profiles for all portfolio positions

This script:
1. Gets all unique symbols from active positions
2. Fetches company profile data from yahooquery
3. Updates the company_profiles table with sector, industry, and other data
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.services.market_data_service import MarketDataService
from app.core.logging import get_logger

logger = get_logger(__name__)


async def sync_all_company_profiles():
    """Sync company profiles for all portfolio symbols"""
    logger.info("Starting company profile sync")

    async with AsyncSessionLocal() as db:
        # Get all unique symbols from active positions
        symbols_result = await db.execute(
            select(Position.symbol)
            .distinct()
            .where(Position.deleted_at.is_(None))
        )
        symbols = [row[0] for row in symbols_result.all()]

        logger.info(f"Found {len(symbols)} unique symbols to sync")

        # Use the market data service's batch method
        market_data_service = MarketDataService()

        # Fetch and cache all company profiles in batches
        result = await market_data_service.fetch_and_cache_company_profiles(
            db=db,
            symbols=symbols
        )

        logger.info(
            f"\nCompany profile sync complete:\n"
            f"  Attempted: {result['symbols_attempted']}\n"
            f"  Successful: {result['symbols_successful']}\n"
            f"  Failed: {result['symbols_failed']}\n"
            f"  Failed symbols: {result['failed_symbols'][:10] if result['failed_symbols'] else 'None'}"
        )

        return {
            'success': result['symbols_failed'] < result['symbols_attempted'],
            'synced': result['symbols_successful'],
            'errors': result['symbols_failed'],
            'total': result['symbols_attempted'],
            'failed_symbols': result['failed_symbols']
        }


async def main():
    """Run company profile sync"""
    print("=" * 60)
    print("COMPANY PROFILE SYNC")
    print("=" * 60)

    result = await sync_all_company_profiles()

    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print(f"\nResults:")
    print(f"  Total symbols: {result['total']}")
    print(f"  Synced: {result['synced']}")
    print(f"  Errors: {result['errors']}")

    if result['errors'] > 0 and result.get('failed_symbols'):
        print(f"\nFailed symbols (first 10): {result['failed_symbols'][:10]}")

    if result['synced'] > 0:
        print("\nNext steps:")
        print("  1. Verify company profiles were synced:")
        print("     python scripts/verification/test_sector_tagging.py")
        print("")
        print("  2. Restore sector tags for all positions:")
        print("     python scripts/restore_sector_tags.py")
    else:
        print("\n[WARN] No profiles were synced successfully. Check logs for errors.")


if __name__ == "__main__":
    asyncio.run(main())
