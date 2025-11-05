"""Run batch calculations to fix equity balance"""
import asyncio
from datetime import date
from app.database import AsyncSessionLocal
from app.batch.batch_orchestrator import batch_orchestrator
from app.utils.trading_calendar import trading_calendar

async def run_batch():
    print("=" * 80)
    print("RUNNING BATCH CALCULATIONS TO FIX EQUITY")
    print("=" * 80)
    print()

    async with AsyncSessionLocal() as db:
        # Use Oct 29, 2024 - the most recent date with complete market data
        # (Avoids trying to fetch data for future dates or weekends)
        calculation_date = date(2024, 10, 29)
        print(f"Using calculation date: {calculation_date} (most recent with complete data)")
        print()

        await batch_orchestrator.run_daily_batch_sequence(db=db, calculation_date=calculation_date)

    print()
    print("=" * 80)
    print("BATCH COMPLETE!")
    print("=" * 80)

asyncio.run(run_batch())
