"""
Populate company_profiles table by fetching data from yahooquery for all position symbols.
Run this script to backfill company profiles for existing positions.
"""
import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.market_data import CompanyProfile
from app.services.market_data_service import market_data_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Fetch and store company profiles for all unique position symbols."""

    async with AsyncSessionLocal() as db:
        try:
            # Get all unique symbols from positions table
            logger.info("Fetching unique symbols from positions table...")
            stmt = select(Position.symbol).distinct()
            result = await db.execute(stmt)
            symbols = [row[0] for row in result.all()]

            logger.info(f"Found {len(symbols)} unique symbols")

            if not symbols:
                logger.warning("No symbols found in positions table")
                return

            # Batch process symbols (10 at a time to avoid rate limits)
            batch_size = 10
            total_batches = (len(symbols) + batch_size - 1) // batch_size

            total_success = 0
            total_failed = 0

            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                batch_num = (i // batch_size) + 1

                logger.info(f"\nProcessing batch {batch_num}/{total_batches}: {batch}")

                try:
                    # Fetch and cache profiles for this batch
                    # Phase 9.0: Returns detailed results dict instead of Dict[str, bool]
                    results = await market_data_service.fetch_and_cache_company_profiles(
                        db, batch
                    )

                    # Count successes and failures from new return format
                    batch_success = results['symbols_successful']
                    batch_failed = results['symbols_failed']

                    total_success += batch_success
                    total_failed += batch_failed

                    logger.info(
                        f"Batch {batch_num}: {batch_success}/{len(batch)} successful, "
                        f"{batch_failed} failed"
                    )

                    # Log individual failures
                    if results['failed_symbols']:
                        for symbol in results['failed_symbols']:
                            logger.warning(f"  Failed to fetch profile for {symbol}")

                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
                    total_failed += len(batch)

                # Sleep between batches to respect rate limits
                if i + batch_size < len(symbols):
                    logger.info("Sleeping 1 second before next batch...")
                    await asyncio.sleep(1)

            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info("POPULATION COMPLETE")
            logger.info(f"Total symbols processed: {len(symbols)}")
            logger.info(f"Successful: {total_success}")
            logger.info(f"Failed: {total_failed}")
            logger.info("=" * 60)

            # Show sample of stored profiles
            logger.info("\nSample of stored profiles:")
            stmt = select(CompanyProfile).limit(5)
            result = await db.execute(stmt)
            profiles = result.scalars().all()

            for profile in profiles:
                cy_rev = profile.current_year_revenue_avg
                ny_rev = profile.next_year_revenue_avg
                cy_rev_str = f"${cy_rev/1e9:.1f}B" if cy_rev else "N/A"
                ny_rev_str = f"${ny_rev/1e9:.1f}B" if ny_rev else "N/A"

                logger.info(
                    f"  {profile.symbol}: {profile.company_name or 'N/A'} | "
                    f"Beta: {profile.beta or 'N/A'} | "
                    f"CY Rev: {cy_rev_str} | NY Rev: {ny_rev_str}"
                )

        except Exception as e:
            logger.error(f"Fatal error in main: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
