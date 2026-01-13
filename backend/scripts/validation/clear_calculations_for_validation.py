#!/usr/bin/env python
"""
Clear Calculations for V2 Batch Validation

This script clears calculated data for the 3 demo portfolios for a date range,
while PRESERVING market_data_cache (historical prices) needed for recalculation.

Usage:
    # Dry run (preview only, no deletions)
    python scripts/validation/clear_calculations_for_validation.py --dry-run

    # Actually clear the data
    python scripts/validation/clear_calculations_for_validation.py

Tables Cleared:
    - portfolio_snapshots (filtered by portfolio_id + date)
    - symbol_factor_exposures (for symbols in demo portfolios, by date)
    - factor_exposures (portfolio-level, filtered by portfolio_id + date)
    - correlation_calculations + pairwise_correlations (filtered by portfolio_id + date)
    - stress_test_results (filtered by portfolio_id + date)

Tables PRESERVED:
    - market_data_cache (historical prices - needed for recalculation)
    - company_profiles
    - positions, portfolios, users
"""
import sys
import asyncio
import argparse
from datetime import date
from pathlib import Path
from typing import List
from uuid import UUID

# CRITICAL: Windows + asyncpg compatibility fix - MUST be before any async imports
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Railway DATABASE_URL (convert to asyncpg if needed)
DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

# Date range for validation
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 1, 12)

# Demo user emails
DEMO_EMAILS = [
    "demo_individual@sigmasight.com",
    "demo_hnw@sigmasight.com",
    "demo_hedgefundstyle@sigmasight.com",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Clear calculations for V2 batch validation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletions without actually deleting"
    )
    return parser.parse_args()


async def get_demo_portfolio_ids(session: AsyncSession) -> List[str]:
    """Get portfolio IDs for the 3 demo users."""
    from app.models.users import User, Portfolio

    portfolio_ids = []

    for email in DEMO_EMAILS:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"  [WARN] User not found: {email}")
            continue

        result = await session.execute(
            select(Portfolio).where(
                and_(
                    Portfolio.user_id == user.id,
                    Portfolio.deleted_at.is_(None)
                )
            )
        )
        user_portfolios = result.scalars().all()

        for portfolio in user_portfolios:
            portfolio_ids.append(str(portfolio.id))
            print(f"  Found portfolio: {portfolio.name} ({portfolio.id})")

    return portfolio_ids


async def get_symbols_in_portfolios(session: AsyncSession, portfolio_ids: List[str]) -> List[str]:
    """Get all symbols in the demo portfolios."""
    from app.models.positions import Position

    result = await session.execute(
        select(Position.symbol).where(
            and_(
                Position.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                Position.exit_date.is_(None),
            )
        ).distinct()
    )
    symbols = [row[0].upper() for row in result.fetchall() if row[0]]
    return symbols


async def count_portfolio_snapshots(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Count portfolio_snapshots to be deleted."""
    from app.models.snapshots import PortfolioSnapshot

    result = await session.execute(
        select(func.count(PortfolioSnapshot.id)).where(
            and_(
                PortfolioSnapshot.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                PortfolioSnapshot.snapshot_date >= start_date,
                PortfolioSnapshot.snapshot_date <= end_date,
            )
        )
    )
    return result.scalar() or 0


async def delete_portfolio_snapshots(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Delete portfolio_snapshots for the date range."""
    from app.models.snapshots import PortfolioSnapshot

    result = await session.execute(
        delete(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                PortfolioSnapshot.snapshot_date >= start_date,
                PortfolioSnapshot.snapshot_date <= end_date,
            )
        )
    )
    return result.rowcount


async def count_symbol_factor_exposures(
    session: AsyncSession,
    symbols: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Count symbol_factor_exposures to be deleted."""
    from app.models.symbol_analytics import SymbolFactorExposure

    if not symbols:
        return 0

    result = await session.execute(
        select(func.count(SymbolFactorExposure.id)).where(
            and_(
                SymbolFactorExposure.symbol.in_(symbols),
                SymbolFactorExposure.calculation_date >= start_date,
                SymbolFactorExposure.calculation_date <= end_date,
            )
        )
    )
    return result.scalar() or 0


async def delete_symbol_factor_exposures(
    session: AsyncSession,
    symbols: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Delete symbol_factor_exposures for the date range."""
    from app.models.symbol_analytics import SymbolFactorExposure

    if not symbols:
        return 0

    result = await session.execute(
        delete(SymbolFactorExposure).where(
            and_(
                SymbolFactorExposure.symbol.in_(symbols),
                SymbolFactorExposure.calculation_date >= start_date,
                SymbolFactorExposure.calculation_date <= end_date,
            )
        )
    )
    return result.rowcount


async def count_factor_exposures(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Count factor_exposures to be deleted."""
    from app.models.market_data import FactorExposure

    result = await session.execute(
        select(func.count(FactorExposure.id)).where(
            and_(
                FactorExposure.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                FactorExposure.calculation_date >= start_date,
                FactorExposure.calculation_date <= end_date,
            )
        )
    )
    return result.scalar() or 0


async def delete_factor_exposures(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Delete factor_exposures for the date range."""
    from app.models.market_data import FactorExposure

    result = await session.execute(
        delete(FactorExposure).where(
            and_(
                FactorExposure.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                FactorExposure.calculation_date >= start_date,
                FactorExposure.calculation_date <= end_date,
            )
        )
    )
    return result.rowcount


async def count_correlation_data(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> dict:
    """Count correlation data to be deleted."""
    from app.models.correlations import CorrelationCalculation, PairwiseCorrelation

    # Count correlation_calculations
    result = await session.execute(
        select(func.count(CorrelationCalculation.id)).where(
            and_(
                CorrelationCalculation.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                CorrelationCalculation.calculation_date >= start_date,
                CorrelationCalculation.calculation_date <= end_date,
            )
        )
    )
    calc_count = result.scalar() or 0

    # Get correlation_calculation IDs to count pairwise
    result = await session.execute(
        select(CorrelationCalculation.id).where(
            and_(
                CorrelationCalculation.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                CorrelationCalculation.calculation_date >= start_date,
                CorrelationCalculation.calculation_date <= end_date,
            )
        )
    )
    calc_ids = [row[0] for row in result.fetchall()]

    pair_count = 0
    if calc_ids:
        result = await session.execute(
            select(func.count(PairwiseCorrelation.id)).where(
                PairwiseCorrelation.correlation_calculation_id.in_(calc_ids)
            )
        )
        pair_count = result.scalar() or 0

    return {"calculations": calc_count, "pairwise": pair_count}


async def delete_correlation_data(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> dict:
    """Delete correlation data for the date range."""
    from app.models.correlations import CorrelationCalculation, PairwiseCorrelation

    # First get the calculation IDs
    result = await session.execute(
        select(CorrelationCalculation.id).where(
            and_(
                CorrelationCalculation.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                CorrelationCalculation.calculation_date >= start_date,
                CorrelationCalculation.calculation_date <= end_date,
            )
        )
    )
    calc_ids = [row[0] for row in result.fetchall()]

    # Delete pairwise_correlations first (foreign key constraint)
    pair_deleted = 0
    if calc_ids:
        result = await session.execute(
            delete(PairwiseCorrelation).where(
                PairwiseCorrelation.correlation_calculation_id.in_(calc_ids)
            )
        )
        pair_deleted = result.rowcount

    # Then delete correlation_calculations
    result = await session.execute(
        delete(CorrelationCalculation).where(
            and_(
                CorrelationCalculation.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                CorrelationCalculation.calculation_date >= start_date,
                CorrelationCalculation.calculation_date <= end_date,
            )
        )
    )
    calc_deleted = result.rowcount

    return {"calculations": calc_deleted, "pairwise": pair_deleted}


async def count_stress_test_results(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Count stress_test_results to be deleted."""
    from app.models.market_data import StressTestResult

    result = await session.execute(
        select(func.count(StressTestResult.id)).where(
            and_(
                StressTestResult.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                StressTestResult.calculation_date >= start_date,
                StressTestResult.calculation_date <= end_date,
            )
        )
    )
    return result.scalar() or 0


async def delete_stress_test_results(
    session: AsyncSession,
    portfolio_ids: List[str],
    start_date: date,
    end_date: date,
) -> int:
    """Delete stress_test_results for the date range."""
    from app.models.market_data import StressTestResult

    result = await session.execute(
        delete(StressTestResult).where(
            and_(
                StressTestResult.portfolio_id.in_([UUID(pid) for pid in portfolio_ids]),
                StressTestResult.calculation_date >= start_date,
                StressTestResult.calculation_date <= end_date,
            )
        )
    )
    return result.rowcount


async def main():
    args = parse_args()
    dry_run = args.dry_run

    print("=" * 70)
    print("CLEAR CALCULATIONS FOR V2 BATCH VALIDATION")
    print("=" * 70)
    print(f"Date Range: {START_DATE} to {END_DATE}")
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE (will delete data)'}")
    print()

    if not dry_run:
        confirm = input("[WARNING] This will DELETE calculation data. Type 'yes' to continue: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Step 1: Get demo portfolio IDs
        print("Step 1: Finding demo portfolios...")
        portfolio_ids = await get_demo_portfolio_ids(session)
        print(f"  Found {len(portfolio_ids)} portfolios")
        print()

        if not portfolio_ids:
            print("[ERROR] No demo portfolios found!")
            return

        # Get symbols in portfolios (for symbol_factor_exposures)
        symbols = await get_symbols_in_portfolios(session, portfolio_ids)
        print(f"  Found {len(symbols)} symbols in demo portfolios")
        print()

        # Step 2: Count/delete portfolio_snapshots
        print("Step 2: portfolio_snapshots...")
        count = await count_portfolio_snapshots(session, portfolio_ids, START_DATE, END_DATE)
        if dry_run:
            print(f"  Would delete: {count} rows")
        else:
            deleted = await delete_portfolio_snapshots(session, portfolio_ids, START_DATE, END_DATE)
            print(f"  Deleted: {deleted} rows")
        print()

        # Step 3: Count/delete symbol_factor_exposures
        print("Step 3: symbol_factor_exposures...")
        count = await count_symbol_factor_exposures(session, symbols, START_DATE, END_DATE)
        if dry_run:
            print(f"  Would delete: {count} rows")
        else:
            deleted = await delete_symbol_factor_exposures(session, symbols, START_DATE, END_DATE)
            print(f"  Deleted: {deleted} rows")
        print()

        # Step 4: Count/delete factor_exposures
        print("Step 4: factor_exposures (portfolio-level)...")
        count = await count_factor_exposures(session, portfolio_ids, START_DATE, END_DATE)
        if dry_run:
            print(f"  Would delete: {count} rows")
        else:
            deleted = await delete_factor_exposures(session, portfolio_ids, START_DATE, END_DATE)
            print(f"  Deleted: {deleted} rows")
        print()

        # Step 5: Count/delete correlation data
        print("Step 5: correlation_calculations + pairwise_correlations...")
        counts = await count_correlation_data(session, portfolio_ids, START_DATE, END_DATE)
        if dry_run:
            print(f"  Would delete: {counts['calculations']} correlation_calculations")
            print(f"  Would delete: {counts['pairwise']} pairwise_correlations")
        else:
            deleted = await delete_correlation_data(session, portfolio_ids, START_DATE, END_DATE)
            print(f"  Deleted: {deleted['calculations']} correlation_calculations")
            print(f"  Deleted: {deleted['pairwise']} pairwise_correlations")
        print()

        # Step 6: Count/delete stress_test_results
        print("Step 6: stress_test_results...")
        count = await count_stress_test_results(session, portfolio_ids, START_DATE, END_DATE)
        if dry_run:
            print(f"  Would delete: {count} rows")
        else:
            deleted = await delete_stress_test_results(session, portfolio_ids, START_DATE, END_DATE)
            print(f"  Deleted: {deleted} rows")
        print()

        # Commit if not dry run
        if not dry_run:
            await session.commit()
            print("[OK] All deletions committed.")
        else:
            print("[INFO] Dry run complete. No changes made.")

    print()
    print("=" * 70)
    print("CLEAR CALCULATIONS COMPLETE")
    print("=" * 70)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
