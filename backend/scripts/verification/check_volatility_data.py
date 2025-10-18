"""
Check PortfolioSnapshot table for volatility data.

This script checks all portfolios to see if they have snapshot records
with volatility metrics populated.
"""
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio


async def check_volatility_data():
    """Check all portfolios for volatility data in snapshots."""
    async with get_async_session() as db:
        # Get all portfolios
        portfolio_result = await db.execute(select(Portfolio))
        portfolios = portfolio_result.scalars().all()

        print(f"\n{'='*80}")
        print(f"VOLATILITY DATA AUDIT - Found {len(portfolios)} portfolios")
        print(f"{'='*80}\n")

        for portfolio in portfolios:
            print(f"\nPortfolio: {portfolio.name}")
            print(f"Portfolio ID: {portfolio.id}")
            print(f"{'-'*80}")

            # Get latest snapshot for this portfolio
            snapshot_result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            if not snapshot:
                print("[X] NO SNAPSHOT FOUND")
                print("    -> Need to run batch processing to create snapshots\n")
                continue

            print(f"[OK] Snapshot exists: {snapshot.snapshot_date}")
            print(f"\nVolatility Metrics:")

            # Check each volatility field
            if snapshot.realized_volatility_21d is not None:
                print(f"  [OK] 21-day realized: {snapshot.realized_volatility_21d:.4f} ({snapshot.realized_volatility_21d * 100:.2f}%)")
            else:
                print(f"  [X] 21-day realized: NULL")

            if snapshot.realized_volatility_63d is not None:
                print(f"  [OK] 63-day realized: {snapshot.realized_volatility_63d:.4f} ({snapshot.realized_volatility_63d * 100:.2f}%)")
            else:
                print(f"  [!] 63-day realized: NULL")

            if snapshot.expected_volatility_21d is not None:
                print(f"  [OK] Expected (HAR): {snapshot.expected_volatility_21d:.4f} ({snapshot.expected_volatility_21d * 100:.2f}%)")
            else:
                print(f"  [!] Expected (HAR): NULL")

            if snapshot.volatility_trend:
                print(f"  [OK] Trend: {snapshot.volatility_trend}")
            else:
                print(f"  [!] Trend: NULL")

            if snapshot.volatility_percentile is not None:
                print(f"  [OK] Percentile: {snapshot.volatility_percentile:.4f} ({snapshot.volatility_percentile * 100:.1f}th)")
            else:
                print(f"  [!] Percentile: NULL")

            # Summary
            has_all_fields = all([
                snapshot.realized_volatility_21d is not None,
                snapshot.realized_volatility_63d is not None,
                snapshot.expected_volatility_21d is not None,
                snapshot.volatility_trend is not None,
                snapshot.volatility_percentile is not None
            ])

            has_minimum = snapshot.realized_volatility_21d is not None

            if has_all_fields:
                print(f"\n[OK] COMPLETE: All volatility fields populated")
            elif has_minimum:
                print(f"\n[!] PARTIAL: Minimum fields present (21d volatility)")
            else:
                print(f"\n[X] INCOMPLETE: Missing critical volatility data")
                print(f"    -> Need to run batch processing with Phase 2 volatility calculations")

            print()

        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")

        # Count snapshots with volatility data
        snapshot_count_result = await db.execute(
            select(func.count(PortfolioSnapshot.id))
        )
        total_snapshots = snapshot_count_result.scalar()

        volatility_count_result = await db.execute(
            select(func.count(PortfolioSnapshot.id))
            .where(PortfolioSnapshot.realized_volatility_21d.isnot(None))
        )
        snapshots_with_volatility = volatility_count_result.scalar()

        print(f"Total portfolios: {len(portfolios)}")
        print(f"Total snapshots: {total_snapshots}")
        print(f"Snapshots with volatility data: {snapshots_with_volatility}")

        if snapshots_with_volatility == 0:
            print(f"\n[X] NO VOLATILITY DATA FOUND")
            print(f"\nRECOMMENDATION:")
            print(f"  Run: cd backend && uv run python scripts/run_batch_calculations.py")
        elif snapshots_with_volatility < len(portfolios):
            print(f"\n[!] PARTIAL VOLATILITY DATA")
            print(f"\nRECOMMENDATION:")
            print(f"  Run: cd backend && uv run python scripts/run_batch_calculations.py")
        else:
            print(f"\n[OK] ALL PORTFOLIOS HAVE VOLATILITY DATA")

        print()


if __name__ == "__main__":
    asyncio.run(check_volatility_data())
