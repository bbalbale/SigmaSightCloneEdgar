"""
Backfill ALL missing portfolio snapshots (including gaps between existing snapshots).

This script:
1. Finds ALL trading days where market data exists
2. Creates snapshots for any missing dates (even between existing snapshots)
3. Processes dates in chronological order to maintain equity rollforward
"""
import asyncio
from sqlalchemy import text
from datetime import timedelta, date
from app.database import get_async_session
from app.calculations.snapshots import create_portfolio_snapshot
from app.utils.trading_calendar import trading_calendar


async def main():
    print("=" * 80)
    print("BACKFILL ALL MISSING SNAPSHOTS")
    print("=" * 80)
    print()

    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"

    async with get_async_session() as db:
        # Get all dates with market data
        result = await db.execute(text("""
            SELECT DISTINCT date
            FROM market_data_cache
            WHERE date BETWEEN '2025-09-30' AND '2025-10-19'
            ORDER BY date ASC
        """))
        all_market_dates = [row.date for row in result.fetchall()]

        # Get all dates with snapshots
        result2 = await db.execute(text("""
            SELECT DISTINCT snapshot_date
            FROM portfolio_snapshots
            WHERE portfolio_id = :portfolio_id
            AND snapshot_date BETWEEN '2025-09-30' AND '2025-10-19'
            ORDER BY snapshot_date ASC
        """), {"portfolio_id": portfolio_id})
        existing_snapshots = [row.snapshot_date for row in result2.fetchall()]

        # Find missing dates
        missing_dates = [d for d in all_market_dates if d not in existing_snapshots]

        print(f"Market data available: {len(all_market_dates)} trading days")
        print(f"Existing snapshots: {len(existing_snapshots)} snapshots")
        print(f"Missing snapshots: {len(missing_dates)} dates")
        print()

        if not missing_dates:
            print("No missing snapshots to create!")
            return

        print("Missing dates:")
        for md in missing_dates:
            print(f"  - {md}")
        print()

        print("=" * 80)
        print("Creating missing snapshots in chronological order...")
        print("=" * 80)
        print()

        successful = 0
        failed = 0

        for snapshot_date in missing_dates:
            try:
                result = await create_portfolio_snapshot(db, portfolio_id, snapshot_date)

                if result.get('success'):
                    successful += 1
                    snapshot = result['snapshot']
                    print(f"OK {snapshot_date}: equity=${float(snapshot.equity_balance):,.2f}, "
                          f"pnl=${float(snapshot.daily_pnl):,.2f}")
                else:
                    failed += 1
                    print(f"FAILED {snapshot_date}: {result.get('message')}")

            except Exception as e:
                failed += 1
                print(f"ERROR {snapshot_date}: {str(e)}")

        print()
        print("=" * 80)
        print("BACKFILL COMPLETE")
        print("=" * 80)
        print(f"Created: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {successful + failed}")


if __name__ == "__main__":
    asyncio.run(main())
