"""Check what market data dates we have available."""
import asyncio
from sqlalchemy import text
from app.database import get_async_session


async def check():
    async with get_async_session() as db:
        # Get distinct dates from market_data_cache
        result = await db.execute(text("""
            SELECT DISTINCT date
            FROM market_data_cache
            WHERE date BETWEEN '2025-09-30' AND '2025-10-19'
            ORDER BY date ASC
        """))

        dates = [row.date for row in result.fetchall()]

        print("=" * 80)
        print(f"MARKET DATA CACHE - Available Dates")
        print(f"Found {len(dates)} unique dates between Sept 30 and Oct 19")
        print("=" * 80)
        print()

        if dates:
            for i, date in enumerate(dates, 1):
                print(f"{i}. {date}")

            print()
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"First date: {dates[0]}")
            print(f"Last date: {dates[-1]}")
            print(f"Total trading days with data: {len(dates)}")

            # Check how many symbols per date (sample a few dates)
            print()
            print("=" * 80)
            print("SAMPLE: Symbols per Date")
            print("=" * 80)
            for sample_date in dates[::3]:  # Every 3rd date
                result2 = await db.execute(text("""
                    SELECT COUNT(DISTINCT symbol) as symbol_count
                    FROM market_data_cache
                    WHERE date = :date
                """), {"date": sample_date})
                count = result2.scalar()
                print(f"{sample_date}: {count} symbols")

        else:
            print("❌ NO market data found for this date range!")

        print()
        print("=" * 80)
        print("SNAPSHOT COMPARISON")
        print("=" * 80)

        # Get snapshot dates
        result3 = await db.execute(text("""
            SELECT DISTINCT snapshot_date
            FROM portfolio_snapshots
            WHERE snapshot_date BETWEEN '2025-09-30' AND '2025-10-19'
            ORDER BY snapshot_date ASC
        """))

        snapshot_dates = [row.snapshot_date for row in result3.fetchall()]

        print(f"Snapshots exist for {len(snapshot_dates)} dates:")
        for sd in snapshot_dates:
            print(f"  - {sd}")

        print()
        print(f"Market data available but NO snapshot: {len(dates) - len(snapshot_dates)} dates")

        # List missing snapshot dates where we have data
        missing = [d for d in dates if d not in snapshot_dates]
        if missing:
            print("\nMissing snapshots (but have market data):")
            for md in missing[:10]:  # Show first 10
                print(f"  - {md}")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")


if __name__ == "__main__":
    asyncio.run(check())
