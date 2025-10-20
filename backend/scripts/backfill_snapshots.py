"""
Backfill missing portfolio snapshots.

This script:
1. Fixes the Sept 30 snapshot (sets equity_balance to starting equity)
2. Runs the batch orchestrator's snapshot backfill for all portfolios
3. Verifies the results
"""
import asyncio
from sqlalchemy import text
from app.database import get_async_session
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2


async def fix_sept30_snapshot():
    """Fix the Sept 30 snapshot that's missing equity_balance."""
    print("=" * 80)
    print("STEP 1: Fixing Sept 30 Snapshot")
    print("=" * 80)

    async with get_async_session() as db:
        # Check current state
        result = await db.execute(text("""
            SELECT snapshot_date, equity_balance
            FROM portfolio_snapshots
            WHERE snapshot_date = '2025-09-30'
            AND portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
        """))
        row = result.fetchone()

        if row and row.equity_balance is None:
            print(f"Found Sept 30 snapshot with equity_balance = None")

            # Get starting equity from portfolio
            result2 = await db.execute(text("""
                SELECT equity_balance
                FROM portfolios
                WHERE id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            """))
            starting_equity = result2.scalar()

            print(f"Setting equity_balance to starting equity: ${float(starting_equity):,.2f}")

            # Update the snapshot
            await db.execute(text("""
                UPDATE portfolio_snapshots
                SET equity_balance = :equity
                WHERE snapshot_date = '2025-09-30'
                AND portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            """), {"equity": starting_equity})

            await db.commit()
            print("✅ Sept 30 snapshot fixed!")
        else:
            print("Sept 30 snapshot already has equity_balance or doesn't exist")

    print()


async def run_backfill():
    """Run the batch orchestrator to backfill missing snapshots."""
    print("=" * 80)
    print("STEP 2: Running Snapshot Backfill")
    print("=" * 80)
    print()

    # Get the HNW portfolio ID
    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"

    # Run just the snapshot job for this portfolio
    async with get_async_session() as db:
        from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
        result = await batch_orchestrator_v2._create_snapshot(db, portfolio_id)

        print(f"Backfill result:")
        print(f"  Snapshots created: {result.get('snapshots_created', 0)}")
        print(f"  Snapshots failed: {result.get('snapshots_failed', 0)}")
        print(f"  Total dates processed: {result.get('total_dates', 0)}")

        # Show any failures
        if result.get('results'):
            failures = [r for r in result['results'] if not r.get('success')]
            if failures:
                print(f"\n  Failed dates:")
                for f in failures:
                    print(f"    - {f['date']}: {f.get('message') or f.get('error')}")

    print()


async def verify_results():
    """Verify the snapshots were created correctly."""
    print("=" * 80)
    print("STEP 3: Verifying Results")
    print("=" * 80)

    async with get_async_session() as db:
        result = await db.execute(text("""
            SELECT
                snapshot_date,
                equity_balance,
                daily_pnl,
                cumulative_pnl,
                total_value
            FROM portfolio_snapshots
            WHERE portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            ORDER BY snapshot_date ASC
        """))

        rows = result.fetchall()

        print(f"\nTotal snapshots: {len(rows)}")
        print(f"Date range: {rows[0].snapshot_date} to {rows[-1].snapshot_date}")
        print()

        # Show summary of each snapshot
        print("Date         | Equity Balance  | Daily P&L      | Cumulative P&L | Total Value")
        print("-" * 85)

        for row in rows:
            equity = f"${float(row.equity_balance):>13,.2f}" if row.equity_balance else "         None"
            pnl = f"${float(row.daily_pnl):>12,.2f}" if row.daily_pnl is not None else "        None"
            cum_pnl = f"${float(row.cumulative_pnl):>13,.2f}" if row.cumulative_pnl is not None else "         None"
            total = f"${float(row.total_value):>12,.2f}" if row.total_value else "        None"

            print(f"{row.snapshot_date} | {equity} | {pnl} | {cum_pnl} | {total}")

        print()

        # Check equity rollforward
        print("Equity Rollforward Check:")
        print("-" * 80)

        for i in range(1, len(rows)):
            prev_row = rows[i-1]
            curr_row = rows[i]

            if prev_row.equity_balance and curr_row.equity_balance and curr_row.daily_pnl is not None:
                expected_equity = float(prev_row.equity_balance) + float(curr_row.daily_pnl)
                actual_equity = float(curr_row.equity_balance)
                diff = actual_equity - expected_equity

                if abs(diff) > 0.01:  # Allow for small rounding
                    print(f"❌ {curr_row.snapshot_date}: Expected ${expected_equity:,.2f}, got ${actual_equity:,.2f} (diff: ${diff:,.2f})")
                else:
                    print(f"✅ {curr_row.snapshot_date}: Equity rolled forward correctly from ${float(prev_row.equity_balance):,.2f}")
            elif curr_row.equity_balance is None:
                print(f"⚠️  {curr_row.snapshot_date}: equity_balance is None")
            elif curr_row.daily_pnl is None:
                print(f"⚠️  {curr_row.snapshot_date}: daily_pnl is None (expected for first snapshot)")

        print()
        print("=" * 80)
        print("Backfill Complete!")
        print("=" * 80)


async def main():
    """Run the complete backfill process."""
    print()
    print("=" * 80)
    print(" " * 20 + "PORTFOLIO SNAPSHOT BACKFILL")
    print("=" * 80)
    print()

    try:
        await fix_sept30_snapshot()
        await run_backfill()
        await verify_results()

    except Exception as e:
        print(f"\n❌ Error during backfill: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
