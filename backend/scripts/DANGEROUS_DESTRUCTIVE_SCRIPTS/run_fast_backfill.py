"""
Fast P&L + Analytics Backfill (Skip Market Data Collection)

Assumptions:
- Market data already exists in cache
- Position entry dates are July 1, 2025
- We only need to run P&L calculation + analytics phases
- Skip coverage checking for 19 non-public symbols (privates + options)
"""
import asyncio
from datetime import date, timedelta
from app.database import AsyncSessionLocal
from app.batch.pnl_calculator import pnl_calculator
from app.batch.analytics_runner import analytics_runner
from app.utils.trading_calendar import trading_calendar
from app.core.logging import get_logger

logger = get_logger(__name__)

async def run_fast_backfill():
    """Run P&L + Analytics for all trading days from July 1, 2025 to today"""

    print("=" * 80)
    print("FAST P&L + ANALYTICS BACKFILL")
    print("=" * 80)
    print()
    print("Skipping market data collection - using existing cache")
    print("Processing only public equities (57 symbols)")
    print("Skipping 19 privates/options")
    print()

    # Date range
    start_date = date(2025, 7, 1)
    end_date = date.today()
    if not trading_calendar.is_trading_day(end_date):
        previous = trading_calendar.get_previous_trading_day(end_date)
        if previous:
            end_date = previous

    # Get all trading days
    trading_days = []
    current = start_date
    while current <= end_date:
        if trading_calendar.is_trading_day(current):
            trading_days.append(current)
        current += timedelta(days=1)

    print(f"Date range: {start_date} to {end_date}")
    print(f"Trading days to process: {len(trading_days)}")
    print(f"Estimated time: ~{len(trading_days) * 4} minutes ({(len(trading_days) * 4) / 60:.1f} hours)")
    print()

    # Process each trading day
    start_time = asyncio.get_event_loop().time()
    success_count = 0

    for idx, trading_day in enumerate(trading_days, 1):
        day_start = asyncio.get_event_loop().time()

        print(f"[{idx}/{len(trading_days)}] Processing {trading_day}...", end=" ", flush=True)

        try:
            async with AsyncSessionLocal() as db:
                # Phase 2: P&L Calculation (all portfolios)
                await pnl_calculator.calculate_all_portfolios_pnl(
                    calculation_date=trading_day,
                    db=db
                )

                # Phase 3: Analytics (all portfolios)
                await analytics_runner.run_all_portfolios_analytics(
                    calculation_date=trading_day,
                    db=db,
                    run_sector_analysis=True,
                )

                await db.commit()

            day_duration = asyncio.get_event_loop().time() - day_start
            success_count += 1
            print(f"[OK] ({day_duration:.1f}s)")

        except Exception as e:
            day_duration = asyncio.get_event_loop().time() - day_start
            print(f"✗ ({day_duration:.1f}s) - {str(e)[:50]}")
            logger.error(f"Failed to process {trading_day}: {e}")

    total_duration = asyncio.get_event_loop().time() - start_time

    print()
    print("=" * 80)
    print(f"BACKFILL COMPLETE")
    print("=" * 80)
    print(f"Success: {success_count}/{len(trading_days)} days")
    print(f"Duration: {total_duration:.0f}s ({total_duration/60:.1f} minutes)")
    print(f"Avg per day: {total_duration/len(trading_days):.1f}s")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_fast_backfill())
