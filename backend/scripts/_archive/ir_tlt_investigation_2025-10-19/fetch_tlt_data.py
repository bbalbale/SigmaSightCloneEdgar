"""
Fetch TLT (20+ Year Treasury Bond ETF) Historical Data
Required for TLT-based Interest Rate Beta analysis
"""
import asyncio
from datetime import date, timedelta
from app.database import get_async_session
from app.services.market_data_service import market_data_service
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_tlt_historical_data():
    """Fetch TLT historical price data for IR beta calculations"""

    # Need 90 days + buffer for regression
    end_date = date.today()
    start_date = end_date - timedelta(days=180)  # 6 months of data

    logger.info(f"Fetching TLT data from {start_date} to {end_date}")

    async with get_async_session() as db:
        # Fetch and cache TLT price data
        stats = await market_data_service.update_market_data_cache(
            db=db,
            symbols=['TLT'],
            start_date=start_date,
            end_date=end_date,
            include_gics=False
        )

        if stats['records_inserted'] > 0 or stats['records_skipped'] > 0:
            total_records = stats['records_inserted'] + stats['records_skipped']
            logger.info(f"[OK] Successfully cached {total_records} days of TLT data")
            logger.info(f"   New records: {stats['records_inserted']}, Already cached: {stats['records_skipped']}")

            # Verify by querying the cache
            from sqlalchemy import select, func
            from app.models.market_data import MarketDataCache

            count_stmt = select(func.count(MarketDataCache.id)).where(MarketDataCache.symbol == 'TLT')
            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar()

            # Get sample prices
            sample_stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == 'TLT'
            ).order_by(MarketDataCache.date.desc()).limit(5)
            sample_result = await db.execute(sample_stmt)
            sample_records = sample_result.scalars().all()

            print("\nSample TLT prices (last 5 days):")
            for record in sample_records:
                print(f"  {record.date}: ${record.close:.2f}")

            logger.info(f"Total TLT records in database: {total_count}")
        else:
            logger.error("[FAIL] Failed to fetch TLT data")
            return False

    return True


if __name__ == "__main__":
    success = asyncio.run(fetch_tlt_historical_data())

    if success:
        print("\n" + "=" * 80)
        print("TLT Data Fetch Complete")
        print("=" * 80)
        print("You can now run: uv run python scripts/save_tlt_ir_results.py")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("TLT Data Fetch FAILED")
        print("=" * 80)
        print("Check API keys and network connection")
