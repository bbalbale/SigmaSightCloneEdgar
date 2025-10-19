"""
Script to fetch and store historical Treasury yield data in market_data_cache
This ensures Treasury data is available for interest rate beta calculations

Usage:
    uv run python scripts/fetch_treasury_data.py
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from fredapi import Fred
from sqlalchemy import select, and_

from app.database import get_async_session
from app.models.market_data import MarketDataCache
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_and_store_treasury_data(
    symbol: str = "DGS10",
    days_back: int = 365,
    description: str = "10-Year Treasury Constant Maturity Rate"
):
    """
    Fetch historical Treasury yield data from FRED and store in market_data_cache

    Args:
        symbol: FRED series ID (DGS10 = 10-Year Treasury)
        days_back: Number of days of historical data to fetch (default 365)
        description: Description of the series
    """
    logger.info(f"Fetching {symbol} Treasury data for past {days_back} days...")

    # Check if FRED API key is configured
    if not settings.FRED_API_KEY:
        logger.error("FRED_API_KEY not configured in .env file")
        logger.info("Please add: FRED_API_KEY=your_key_here to backend/.env")
        return

    try:
        # Initialize FRED API
        fred = Fred(api_key=settings.FRED_API_KEY)

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Fetch Treasury yield data
        logger.info(f"Fetching data from FRED API: {start_date} to {end_date}")
        treasury_data = fred.get_series(
            symbol,
            observation_start=start_date,
            observation_end=end_date
        )

        if treasury_data.empty:
            logger.warning(f"No data returned from FRED for {symbol}")
            return

        logger.info(f"Retrieved {len(treasury_data)} data points from FRED")

        # Store in database
        async with get_async_session() as db:
            records_added = 0
            records_updated = 0

            for data_date, yield_value in treasury_data.items():
                # Skip NaN values (weekends/holidays)
                if yield_value != yield_value:  # NaN check
                    continue

                # Convert pandas timestamp to date
                data_date = data_date.date()

                # Check if record already exists
                stmt = select(MarketDataCache).where(
                    and_(
                        MarketDataCache.symbol == symbol,
                        MarketDataCache.date == data_date
                    )
                )
                result = await db.execute(stmt)
                existing_record = result.scalar_one_or_none()

                # Treasury yields are percentages (e.g., 4.5 for 4.5%)
                # Store as closing price for consistency with equity data
                close_price = Decimal(str(yield_value))

                if existing_record:
                    # Update existing record
                    existing_record.close = close_price
                    existing_record.open = close_price  # Yields don't have intraday variation
                    existing_record.high = close_price
                    existing_record.low = close_price
                    records_updated += 1
                else:
                    # Create new record
                    new_record = MarketDataCache(
                        symbol=symbol,
                        date=data_date,
                        open=close_price,
                        high=close_price,
                        low=close_price,
                        close=close_price,
                        volume=None,  # Treasury data doesn't have volume
                        data_source="FRED"
                    )
                    db.add(new_record)
                    records_added += 1

            # Commit all changes
            await db.commit()

            logger.info(f"✅ Treasury data stored successfully:")
            logger.info(f"   - {records_added} new records added")
            logger.info(f"   - {records_updated} existing records updated")
            logger.info(f"   - Total: {records_added + records_updated} data points")

            # Verify storage
            stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol
            )
            result = await db.execute(stmt)
            all_records = result.scalars().all()

            if all_records:
                dates = [r.date for r in all_records]
                logger.info(f"   - Date range in database: {min(dates)} to {max(dates)}")

    except Exception as e:
        logger.error(f"Error fetching Treasury data: {str(e)}")
        raise


async def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("Treasury Data Fetcher - V1.0")
    logger.info("=" * 60)

    # Fetch 10-Year Treasury data (most commonly used for IR sensitivity)
    await fetch_and_store_treasury_data(
        symbol="DGS10",
        days_back=365,  # 1 year of data for robust regression
        description="10-Year Treasury Constant Maturity Rate"
    )

    logger.info("=" * 60)
    logger.info("Treasury data fetch complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
