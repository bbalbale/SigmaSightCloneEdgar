"""
Backfill TLT (20+ Year Treasury Bond ETF) historical data into market_data_cache.

This script ensures TLT data is available for Interest Rate Beta calculations.
TLT is used as the benchmark for measuring portfolio sensitivity to interest rate changes.

Usage:
    uv run python scripts/database/backfill_tlt_data.py

Date Range: Jan 1, 2024 - Nov 30, 2025
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.services.market_data_service import market_data_service
from app.core.logging import get_logger

logger = get_logger(__name__)


async def backfill_tlt_data():
    """Backfill TLT historical price data from Jan 2024 to Nov 2025"""

    symbol = 'TLT'
    start_date = date(2024, 1, 1)
    end_date = date(2025, 11, 30)

    logger.info(f"Starting TLT backfill from {start_date} to {end_date}")

    async with AsyncSessionLocal() as db:
        # Check existing data
        existing_stmt = select(MarketDataCache).where(
            and_(
                MarketDataCache.symbol == symbol,
                MarketDataCache.date >= start_date,
                MarketDataCache.date <= end_date
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing_records = existing_result.scalars().all()

        existing_dates = {record.date for record in existing_records}
        logger.info(f"Found {len(existing_dates)} existing TLT records in database")

        # Fetch historical data from YFinance using yfinance library directly
        logger.info(f"Fetching TLT data from YFinance...")
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                logger.error("No historical data returned from YFinance")
                return

            logger.info(f"Retrieved {len(hist)} days of data from YFinance")

            # Insert new records
            new_records = 0
            updated_records = 0

            for idx, row in hist.iterrows():
                data_date = idx.date()  # Convert pandas Timestamp to date

                # Check if record exists
                if data_date in existing_dates:
                    # Update existing record if prices differ
                    existing_record = next(r for r in existing_records if r.date == data_date)

                    if (existing_record.close != Decimal(str(row['Close'])) or
                        existing_record.open != Decimal(str(row['Open'])) or
                        existing_record.high != Decimal(str(row['High'])) or
                        existing_record.low != Decimal(str(row['Low']))):

                        existing_record.open = Decimal(str(row['Open']))
                        existing_record.high = Decimal(str(row['High']))
                        existing_record.low = Decimal(str(row['Low']))
                        existing_record.close = Decimal(str(row['Close']))
                        existing_record.volume = int(row['Volume']) if row['Volume'] else None
                        existing_record.data_source = 'yfinance'
                        updated_records += 1
                else:
                    # Create new record
                    from uuid import uuid4
                    new_record = MarketDataCache(
                        id=uuid4(),
                        symbol=symbol,
                        date=data_date,
                        open=Decimal(str(row['Open'])),
                        high=Decimal(str(row['High'])),
                        low=Decimal(str(row['Low'])),
                        close=Decimal(str(row['Close'])),
                        volume=int(row['Volume']) if row['Volume'] else None,
                        data_source='yfinance',
                        sector=None,
                        industry=None,
                        exchange=None,
                        country='US',
                        market_cap=None
                    )
                    db.add(new_record)
                    new_records += 1

            # Commit changes
            await db.commit()

            logger.info(f"[OK] TLT backfill complete!")
            logger.info(f"   New records: {new_records}")
            logger.info(f"   Updated records: {updated_records}")
            logger.info(f"   Total TLT records in database: {len(existing_dates) + new_records}")

            # Verify the data
            verify_stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)
            verify_result = await db.execute(verify_stmt)
            all_records = verify_result.scalars().all()

            if all_records:
                first_date = all_records[0].date
                last_date = all_records[-1].date
                logger.info(f"   Date range: {first_date} to {last_date}")
                logger.info(f"   Sample prices: {first_date}=${all_records[0].close}, {last_date}=${all_records[-1].close}")

        except Exception as e:
            logger.error(f"Error fetching TLT data: {e}")
            raise


async def main():
    """Main entry point"""
    print("=" * 80)
    print("TLT (20+ Year Treasury Bond ETF) Data Backfill")
    print("=" * 80)
    print()
    print("This script will backfill TLT historical data for Interest Rate Beta calculations.")
    print("Date Range: Jan 1, 2024 - Nov 30, 2025")
    print()

    try:
        await backfill_tlt_data()
        print()
        print("=" * 80)
        print("[OK] Backfill completed successfully!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. TLT data is now available in market_data_cache")
        print("  2. TLT will be automatically collected in future Phase 1 market data runs")
        print("  3. Run batch processing to calculate IR Beta with the new TLT data")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print(f"[ERROR] Backfill failed: {e}")
        print("=" * 80)
        raise


if __name__ == "__main__":
    asyncio.run(main())
