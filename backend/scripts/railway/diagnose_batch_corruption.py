"""
Diagnostic Script: Identify Batch Processing Corruption Patterns

This script queries the Railway database to check for:
1. Duplicate snapshots for the same date (shouldn't exist due to unique constraint)
2. Multiple batch runs for the same date
3. Equity rollforward anomalies (equity jumping unexpectedly)
4. Missing snapshots that would cause equity resets

Usage:
    railway run python scripts/railway/diagnose_batch_corruption.py
"""
import asyncio
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any

# Fix Railway DATABASE_URL format BEFORE imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver")

from sqlalchemy import select, func, and_, desc
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.models.batch_tracking import BatchRunTracking


async def check_duplicate_snapshots():
    """Check for duplicate snapshots (shouldn't exist due to unique constraint)"""
    print("\n" + "=" * 80)
    print("1. CHECKING FOR DUPLICATE SNAPSHOTS")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # Group by portfolio_id and snapshot_date, find duplicates
        query = select(
            PortfolioSnapshot.portfolio_id,
            PortfolioSnapshot.snapshot_date,
            func.count(PortfolioSnapshot.id).label('count')
        ).group_by(
            PortfolioSnapshot.portfolio_id,
            PortfolioSnapshot.snapshot_date
        ).having(
            func.count(PortfolioSnapshot.id) > 1
        )

        result = await db.execute(query)
        duplicates = result.all()

        if duplicates:
            print(f"❌ FOUND {len(duplicates)} DUPLICATE SNAPSHOTS!")
            for dup in duplicates:
                print(f"   Portfolio: {dup.portfolio_id}, Date: {dup.snapshot_date}, Count: {dup.count}")
        else:
            print("✅ No duplicate snapshots found (good - unique constraint working)")


async def check_multiple_batch_runs():
    """Check if same date was processed multiple times"""
    print("\n" + "=" * 80)
    print("2. CHECKING FOR MULTIPLE BATCH RUNS ON SAME DATE")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # Get all batch runs, grouped by date
        query = select(
            BatchRunTracking.run_date,
            func.count(BatchRunTracking.id).label('count'),
            func.array_agg(BatchRunTracking.created_at).label('run_times')
        ).group_by(
            BatchRunTracking.run_date
        ).having(
            func.count(BatchRunTracking.id) > 1
        ).order_by(desc(BatchRunTracking.run_date))

        result = await db.execute(query)
        multiple_runs = result.all()

        if multiple_runs:
            print(f"⚠️  FOUND {len(multiple_runs)} DATES WITH MULTIPLE BATCH RUNS:")
            for run in multiple_runs:
                print(f"   Date: {run.run_date}, Runs: {run.count}, Times: {run.run_times}")
            print("\n   This indicates the batch orchestrator ran the same date multiple times!")
        else:
            print("✅ No duplicate batch runs found (each date processed once)")


async def check_equity_rollforward():
    """Check for equity balance anomalies across snapshots"""
    print("\n" + "=" * 80)
    print("3. CHECKING EQUITY ROLLFORWARD INTEGRITY")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        # Get all portfolios
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = portfolios_result.scalars().all()

        issues_found = []

        for portfolio in portfolios:
            # Get snapshots in chronological order
            snapshots_query = select(PortfolioSnapshot).where(
                PortfolioSnapshot.portfolio_id == portfolio.id
            ).order_by(PortfolioSnapshot.snapshot_date)

            snapshots_result = await db.execute(snapshots_query)
            snapshots = list(snapshots_result.scalars().all())

            if len(snapshots) < 2:
                continue

            print(f"\n   Portfolio: {portfolio.name} (ID: {portfolio.id})")
            print(f"   Current equity_balance: ${portfolio.equity_balance:,.2f}")
            print(f"   Snapshots: {len(snapshots)}")

            # Check equity rollforward logic
            for i in range(1, len(snapshots)):
                prev_snap = snapshots[i-1]
                curr_snap = snapshots[i]

                expected_equity = prev_snap.equity_balance + (curr_snap.daily_pnl or Decimal('0')) + (curr_snap.daily_capital_flow or Decimal('0'))
                actual_equity = curr_snap.equity_balance
                diff = abs(actual_equity - expected_equity)

                if diff > Decimal('0.01'):  # More than 1 cent difference
                    issue = {
                        'portfolio': portfolio.name,
                        'date': curr_snap.snapshot_date,
                        'prev_equity': prev_snap.equity_balance,
                        'daily_pnl': curr_snap.daily_pnl,
                        'daily_flow': curr_snap.daily_capital_flow,
                        'expected_equity': expected_equity,
                        'actual_equity': actual_equity,
                        'difference': diff
                    }
                    issues_found.append(issue)

                    print(f"      ❌ {curr_snap.snapshot_date}:")
                    print(f"         Prev equity: ${prev_snap.equity_balance:,.2f}")
                    print(f"         Daily P&L: ${curr_snap.daily_pnl:,.2f}")
                    print(f"         Daily flow: ${curr_snap.daily_capital_flow or 0:,.2f}")
                    print(f"         Expected: ${expected_equity:,.2f}")
                    print(f"         Actual: ${actual_equity:,.2f}")
                    print(f"         DIFFERENCE: ${diff:,.2f} ⚠️")

        if issues_found:
            print(f"\n   ❌ FOUND {len(issues_found)} EQUITY ROLLFORWARD ANOMALIES!")
        else:
            print(f"\n   ✅ All equity rollforward calculations are consistent")


async def check_missing_snapshots():
    """Check for gaps in snapshot dates that would cause equity reset"""
    print("\n" + "=" * 80)
    print("4. CHECKING FOR MISSING SNAPSHOTS (GAPS IN DATES)")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = portfolios_result.scalars().all()

        from app.utils.trading_calendar import trading_calendar

        total_gaps = 0

        for portfolio in portfolios:
            snapshots_query = select(PortfolioSnapshot.snapshot_date).where(
                PortfolioSnapshot.portfolio_id == portfolio.id
            ).order_by(PortfolioSnapshot.snapshot_date)

            snapshots_result = await db.execute(snapshots_query)
            snapshot_dates = [row[0] for row in snapshots_result.all()]

            if len(snapshot_dates) < 2:
                continue

            # Find trading days between first and last snapshot
            expected_dates = trading_calendar.get_trading_days_between(
                snapshot_dates[0],
                snapshot_dates[-1]
            )

            missing = set(expected_dates) - set(snapshot_dates)

            if missing:
                total_gaps += len(missing)
                print(f"\n   Portfolio: {portfolio.name}")
                print(f"   ❌ Missing {len(missing)} snapshot(s): {sorted(missing)}")
                print(f"      This could cause equity to reset when backfill runs!")

        if total_gaps == 0:
            print("\n   ✅ No gaps in snapshot dates")


async def main():
    print("\n" + "=" * 80)
    print("RAILWAY BATCH CORRUPTION DIAGNOSTIC")
    print("=" * 80)

    await check_duplicate_snapshots()
    await check_multiple_batch_runs()
    await check_equity_rollforward()
    await check_missing_snapshots()

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
