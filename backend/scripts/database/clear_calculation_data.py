#!/usr/bin/env python
"""
Clear Calculation Data Script

This script provides a safe and controlled way to clear calculation-related
data from the database for a specified date range. It is designed to allow
for re-running batch calculations without affecting the underlying market data.

Key Features:
- Targets specific calculation tables only.
- Does NOT touch `market_data_cache` or `company_profiles`.
- Requires a `--start-date` to define the deletion range.
- Includes a `--dry-run` mode to preview changes before executing them.
- Requires a `--confirm` flag for the actual deletion to prevent accidents.
"""

import argparse
import asyncio
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Tuple, Type

# --- Pre-computation Setup ---
# Add project root to path to allow for app module imports
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Load environment variables from .env file at the project root
from dotenv import load_dotenv

dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print("Loaded environment variables from .env file.")
else:
    print("Warning: .env file not found. Assuming environment variables are set.")
# --- End Setup ---

from decimal import Decimal
from sqlalchemy import delete, select, func, update
from sqlalchemy.orm import DeclarativeMeta

from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio, User
from app.models.market_data import (
    FactorCorrelation,
    FactorExposure,
    MarketRiskScenario,
    PositionGreeks,
    PositionFactorExposure,
    PositionInterestRateBeta,
    PositionMarketBeta,
    PositionVolatility,
    StressTestResult,
)
from app.models.correlations import (
    CorrelationCalculation,
    CorrelationCluster,
    CorrelationClusterPosition,
    PairwiseCorrelation,
)
from app.models.positions import Position

# --- Configuration ---
# (model, date attribute name, human label)
TABLES_TO_CLEAR: List[Tuple[Type[DeclarativeMeta], str, str]] = [
    (PortfolioSnapshot, "snapshot_date", "Portfolio snapshots"),
    (PositionGreeks, "calculation_date", "Position greeks"),
    (FactorExposure, "calculation_date", "Portfolio factor exposures"),
    (PositionFactorExposure, "calculation_date", "Position factor exposures"),
    (PositionInterestRateBeta, "calculation_date", "Interest-rate betas"),
    (PositionMarketBeta, "calc_date", "Market betas"),
    (PositionVolatility, "calculation_date", "Position volatility metrics"),
    (MarketRiskScenario, "calculation_date", "Market risk scenarios"),
    (StressTestResult, "calculation_date", "Stress test results"),
    (FactorCorrelation, "calculation_date", "Factor correlations"),
]

# Demo portfolio seed equity balances
# ⚠️ CRITICAL: These represent STARTING CAPITAL (equity balance), NOT position values
# For long/short portfolios, gross exposure can exceed equity balance (leverage)
# See backend/CLAUDE.md "Portfolio Equity & Exposure Definitions" section
DEMO_EQUITY_SEED_VALUES = {
    "demo_individual@sigmasight.com": Decimal("485000.00"),  # No leverage
    "demo_hnw@sigmasight.com": Decimal("2850000.00"),  # No leverage
    "demo_hedgefundstyle@sigmasight.com": Decimal("3200000.00"),  # 1.5x leverage (100% long + 50% short)
    "demo_familyoffice@sigmasight.com": {
        "Demo Family Office Public Growth": Decimal("1250000.00"),  # No leverage
        "Demo Family Office Private Opportunities": Decimal("950000.00"),  # No leverage
    }
}


async def _process_table(
    db,
    table: Type[DeclarativeMeta],
    date_attr: str,
    label: str,
    start_date: date,
    dry_run: bool,
) -> int:
    """Delete rows from a table filtered by the provided date column."""
    table_name = table.__tablename__
    print(f"Processing table: {table_name} ({label})...")

    column = getattr(table, date_attr, None)
    if column is None:
        print(f"  - SKIPPED: Table does not expose '{date_attr}'.")
        return 0

    count_stmt = select(func.count()).where(column >= start_date)
    record_count = (await db.execute(count_stmt)).scalar_one()

    if record_count == 0:
        print("  - No records to delete.")
        return 0

    print(f"  - Found {record_count} records to delete.")

    if not dry_run:
        delete_stmt = delete(table).where(column >= start_date)
        await db.execute(delete_stmt)
        print(f"  - DELETED {record_count} records.")

    return record_count


async def _reset_equity_balances(db, dry_run: bool) -> int:
    """Reset portfolio equity_balance fields to their original seed values."""
    print("Resetting portfolio equity balances to seed values...")

    reset_count = 0

    for user_email, equity_value in DEMO_EQUITY_SEED_VALUES.items():
        # Get user
        user_result = await db.execute(
            select(User).where(User.email == user_email)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            print(f"  - WARNING: User not found: {user_email}")
            continue

        # Handle single portfolio per user
        if isinstance(equity_value, Decimal):
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.user_id == user.id)
            )
            portfolios = portfolio_result.scalars().all()

            if not portfolios:
                print(f"  - WARNING: No portfolios found for user: {user_email}")
                continue

            for portfolio in portfolios:
                old_balance = portfolio.equity_balance
                if not dry_run:
                    portfolio.equity_balance = equity_value
                    db.add(portfolio)

                print(f"  - Reset '{portfolio.name}': {old_balance} -> {equity_value}")
                reset_count += 1

        # Handle multiple portfolios per user (family office case)
        else:
            for portfolio_name, portfolio_equity in equity_value.items():
                portfolio_result = await db.execute(
                    select(Portfolio).where(
                        Portfolio.user_id == user.id,
                        Portfolio.name == portfolio_name
                    )
                )
                portfolio = portfolio_result.scalar_one_or_none()

                if not portfolio:
                    print(f"  - WARNING: Portfolio not found: {portfolio_name} for {user_email}")
                    continue

                old_balance = portfolio.equity_balance
                if not dry_run:
                    portfolio.equity_balance = portfolio_equity
                    db.add(portfolio)

                print(f"  - Reset '{portfolio_name}': {old_balance} -> {portfolio_equity}")
                reset_count += 1

    return reset_count


async def _remove_soft_deleted_positions(db, dry_run: bool) -> int:
    """
    Permanently delete soft-deleted positions (positions with deleted_at IS NOT NULL).

    These positions are already marked as deleted but still exist in the database.
    This function removes them completely to prevent them from appearing in queries
    that don't filter by deleted_at.
    """
    print("Removing soft-deleted positions...")

    # Find all soft-deleted positions
    soft_deleted_positions = (
        await db.execute(
            select(Position).where(
                Position.deleted_at.is_not(None)
            )
        )
    ).scalars().all()

    if not soft_deleted_positions:
        print("  - No soft-deleted positions found.")
        return 0

    # Group by portfolio and symbol for reporting
    from collections import defaultdict
    soft_deleted_by_portfolio = defaultdict(lambda: defaultdict(list))

    for pos in soft_deleted_positions:
        soft_deleted_by_portfolio[pos.portfolio_id][pos.symbol].append(pos)

    total_count = len(soft_deleted_positions)
    print(f"  - Found {total_count} soft-deleted positions to permanently remove:")

    # Print details of what will be deleted
    for portfolio_id, symbols in soft_deleted_by_portfolio.items():
        portfolio = (await db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )).scalar_one_or_none()

        if portfolio:
            print(f"    Portfolio: {portfolio.name}")
            for symbol, positions in symbols.items():
                deleted_dates = [str(p.deleted_at)[:10] for p in positions]
                print(f"      - {symbol}: {len(positions)} soft-deleted (deleted on: {', '.join(set(deleted_dates))})")

    if not dry_run:
        # Permanently delete the soft-deleted positions
        for pos in soft_deleted_positions:
            await db.delete(pos)
        print(f"  - PERMANENTLY DELETED {total_count} soft-deleted positions.")

    return total_count


async def _remove_duplicate_positions(db, dry_run: bool) -> int:
    """
    Remove duplicate positions created after the seed date (June 30, 2025).

    Keeps only positions with entry_date = 2025-06-30 and created before Nov 1, 2025.
    This removes positions that were accidentally created by multiple seed runs or scripts.
    """
    print("Removing duplicate positions created after seed...")

    SEED_DATE = date(2025, 6, 30)
    CUTOFF_CREATED_AT = datetime(2025, 11, 1, 0, 0, 0)  # Keep positions created before Nov 1

    # Find positions to delete: entry_date = June 30 BUT created_at >= Nov 1
    # These are duplicates from later seed runs
    duplicate_positions = (
        await db.execute(
            select(Position).where(
                Position.entry_date == SEED_DATE,
                Position.created_at >= CUTOFF_CREATED_AT,
                Position.deleted_at.is_(None)
            )
        )
    ).scalars().all()

    if not duplicate_positions:
        print("  - No duplicate positions found.")
        return 0

    # Group by portfolio and symbol for reporting
    from collections import defaultdict
    duplicates_by_portfolio = defaultdict(lambda: defaultdict(list))

    for pos in duplicate_positions:
        duplicates_by_portfolio[pos.portfolio_id][pos.symbol].append(pos)

    total_count = len(duplicate_positions)
    print(f"  - Found {total_count} duplicate positions to remove:")

    # Print details of what will be deleted
    for portfolio_id, symbols in duplicates_by_portfolio.items():
        portfolio = (await db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )).scalar_one_or_none()

        if portfolio:
            print(f"    Portfolio: {portfolio.name}")
            for symbol, positions in symbols.items():
                quantities = [str(p.quantity) for p in positions]
                print(f"      - {symbol}: {len(positions)} duplicates (quantities: {', '.join(quantities)})")

    if not dry_run:
        # Delete the duplicate positions
        for pos in duplicate_positions:
            await db.delete(pos)
        print(f"  - DELETED {total_count} duplicate positions.")

    return total_count


async def _clear_correlation_tables(db, start_date: date, dry_run: bool) -> int:
    """Handle correlation calculations and their dependents (clusters, positions, pairwise rows)."""
    print("Processing correlation analytics tables...")

    calculation_ids = (
        await db.execute(
            select(CorrelationCalculation.id).where(CorrelationCalculation.calculation_date >= start_date)
        )
    ).scalars().all()

    if not calculation_ids:
        print("  - No correlation calculations to delete.")
        return 0

    calc_count = len(calculation_ids)

    cluster_ids = (
        await db.execute(
            select(CorrelationCluster.id).where(CorrelationCluster.correlation_calculation_id.in_(calculation_ids))
        )
    ).scalars().all()
    cluster_count = len(cluster_ids)

    cluster_position_count = 0
    if cluster_ids:
        cluster_position_count = (
            await db.execute(
                select(func.count()).where(CorrelationClusterPosition.cluster_id.in_(cluster_ids))
            )
        ).scalar_one()

    pairwise_count = (
        await db.execute(
            select(func.count()).where(PairwiseCorrelation.correlation_calculation_id.in_(calculation_ids))
        )
    ).scalar_one()

    print(
        "  - Pending deletions: "
        f"{calc_count} calculations, {cluster_count} clusters, "
        f"{cluster_position_count} cluster positions, {pairwise_count} pairwise rows."
    )

    if not dry_run:
        if cluster_ids:
            await db.execute(
                delete(CorrelationClusterPosition).where(CorrelationClusterPosition.cluster_id.in_(cluster_ids))
            )
            print(f"  - DELETED {cluster_position_count} cluster positions.")

        await db.execute(
            delete(PairwiseCorrelation).where(PairwiseCorrelation.correlation_calculation_id.in_(calculation_ids))
        )
        print(f"  - DELETED {pairwise_count} pairwise correlation rows.")

        if cluster_ids:
            await db.execute(delete(CorrelationCluster).where(CorrelationCluster.id.in_(cluster_ids)))
            print(f"  - DELETED {cluster_count} correlation clusters.")

        await db.execute(delete(CorrelationCalculation).where(CorrelationCalculation.id.in_(calculation_ids)))
        print(f"  - DELETED {calc_count} correlation calculations.")

    return calc_count + cluster_count + cluster_position_count + pairwise_count


async def clear_data(start_date: date, dry_run: bool, confirm: bool):
    """
    Connects to the database and clears data from the specified tables.
    """
    if not dry_run and not confirm:
        print("ERROR: This is a destructive operation. You must provide the --confirm flag to proceed.")
        print("To see what would be deleted, run with --dry-run.")
        return

    print("--- SigmaSight Calculation Data Clearing Script ---")
    print(f"Start Date: {start_date}")
    print(f"Dry Run Mode: {'Yes' if dry_run else 'No'}")
    print("-" * 50)

    total_deleted_count = 0

    async with get_async_session() as db:
        for table, date_attr, label in TABLES_TO_CLEAR:
            total_deleted_count += await _process_table(
                db=db,
                table=table,
                date_attr=date_attr,
                label=label,
                start_date=start_date,
                dry_run=dry_run,
            )

        total_deleted_count += await _clear_correlation_tables(db, start_date, dry_run)

        # Remove soft-deleted positions (permanently delete them)
        print("\n" + "-" * 50)
        soft_deleted_count = await _remove_soft_deleted_positions(db, dry_run)
        total_deleted_count += soft_deleted_count

        # Remove duplicate positions created after seed
        print("\n" + "-" * 50)
        duplicate_count = await _remove_duplicate_positions(db, dry_run)
        total_deleted_count += duplicate_count

        # Reset equity balances to seed values
        print("\n" + "-" * 50)
        reset_count = await _reset_equity_balances(db, dry_run)
        print(f"Reset {reset_count} portfolio equity balances to seed values.")

        if not dry_run:
            print("\nCommitting changes to the database...")
            await db.commit()
            print("Changes committed.")
        else:
            print("\nRolling back changes (dry run mode)...")
            await db.rollback()
            print("Dry run complete. No changes were made.")

    print("-" * 50)
    if dry_run:
        print(f"Dry run summary: A total of {total_deleted_count} records would be deleted.")
    else:
        print(f"Deletion summary: A total of {total_deleted_count} records were deleted.")
    print("--- Script Finished ---")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clear calculation data from the database.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="The start date (YYYY-MM-DD) from which to clear data (inclusive).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting anything.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required flag to confirm the destructive delete operation.",
    )
    args = parser.parse_args()

    try:
        start_date_obj = date.fromisoformat(args.start_date)
    except ValueError:
        print("ERROR: Invalid date format. Please use YYYY-MM-DD.")
        return

    asyncio.run(clear_data(start_date_obj, args.dry_run, args.confirm))


if __name__ == "__main__":
    main()
