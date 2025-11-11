"""
Backfill net asset value (NAV) and equity balance for portfolios.

This script runs the Phase 2 P&L calculator across a date range so that:
    * Daily P&L is recomputed with the fixed option multiplier logic
    * PortfolioSnapshot.net_asset_value reflects the rolled-forward equity
    * Portfolio.equity_balance is kept in sync with the latest snapshot

Usage examples:
    # Recalc the most recent trading day for all active portfolios
    python -m scripts.analysis.backfill_net_asset_value

    # Recalc a specific date range for a single portfolio
    python -m scripts.analysis.backfill_net_asset_value \\
        --start 2024-10-01 --end 2024-10-31 \\
        --portfolio 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe

    # Preview the work without making changes
    python -m scripts.analysis.backfill_net_asset_value --days 5 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, List, Optional
from uuid import UUID

from sqlalchemy import select

from app.batch.pnl_calculator import pnl_calculator
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.utils.trading_calendar import trading_calendar


ISO_DATE_FMT = "%Y-%m-%d"


def parse_iso_date(value: str) -> date:
    """Convert YYYY-MM-DD string into a date object."""
    return datetime.strptime(value, ISO_DATE_FMT).date()


@dataclass
class BackfillConfig:
    start: date
    end: date
    portfolio_ids: List[UUID]
    dry_run: bool


async def fetch_active_portfolio_ids() -> List[UUID]:
    """Return all active (non-deleted) portfolio IDs."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Portfolio.id).where(Portfolio.deleted_at.is_(None))
        )
        return [row[0] for row in result.fetchall()]


def resolve_trading_days(start: date, end: date) -> List[date]:
    """Return trading days between start/end (inclusive)."""
    if start > end:
        raise ValueError(f"Start date {start} cannot be after end date {end}")

    days = trading_calendar.get_trading_days_between(
        start_date=start,
        end_date=end,
        include_start=True,
        include_end=True,
    )

    if not days:
        raise ValueError("No trading days found in requested range.")

    return days


async def recalc_for_date(
    calc_date: date,
    portfolio_ids: Iterable[UUID],
    dry_run: bool,
) -> tuple[int, int]:
    """
    Run the P&L calculator for each portfolio for the given date.

    Returns:
        (success_count, failure_count)
    """
    if dry_run:
        for pid in portfolio_ids:
            print(f"[DRY RUN] Would recalc NAV for {pid} on {calc_date}")
        return (0, 0)

    success = 0
    failure = 0

    async with AsyncSessionLocal() as session:
        for pid in portfolio_ids:
            try:
                run = await pnl_calculator.calculate_portfolio_pnl(
                    portfolio_id=pid,
                    calculation_date=calc_date,
                    db=session,
                )
                if run:
                    success += 1
                else:
                    failure += 1
                    print(f"[WARN] Snapshot not created for {pid} on {calc_date}")
            except Exception as exc:  # pragma: no cover - defensive logging
                failure += 1
                print(f"[ERROR] Failed to recalc {pid} on {calc_date}: {exc}")

    return success, failure


async def backfill(config: BackfillConfig) -> None:
    """Execute the backfill based on the supplied configuration."""
    portfolio_ids = config.portfolio_ids
    if not portfolio_ids:
        portfolio_ids = await fetch_active_portfolio_ids()
        if not portfolio_ids:
            print("No active portfolios found. Nothing to do.")
            return

    trading_days = resolve_trading_days(config.start, config.end)

    print(
        f"Backfilling NAV for {len(portfolio_ids)} portfolio(s) "
        f"across {len(trading_days)} trading day(s). "
        f"{'(dry run)' if config.dry_run else ''}"
    )

    total_success = 0
    total_failure = 0

    for calc_date in trading_days:
        success, failure = await recalc_for_date(
            calc_date=calc_date,
            portfolio_ids=portfolio_ids,
            dry_run=config.dry_run,
        )
        total_success += success
        total_failure += failure

    print(
        f"Backfill complete. Success: {total_success}, "
        f"Failures: {total_failure}, Dry run: {config.dry_run}"
    )


def build_config(args: argparse.Namespace) -> BackfillConfig:
    """Construct the BackfillConfig from argparse arguments."""
    end = args.end or date.today()
    if trading_calendar.is_trading_day(end) is False:
        maybe_prev = trading_calendar.get_previous_trading_day(end)
        if maybe_prev is None:
            raise ValueError("Unable to resolve previous trading day for end date.")
        end = maybe_prev

    if args.start:
        start = args.start
    elif args.days:
        trading_days = trading_calendar.get_trading_days_between(
            start_date=end,
            end_date=end,
            include_start=True,
            include_end=True,
        )
        if not trading_days:
            raise ValueError("Unable to resolve latest trading day.")
        # get the previous N trading days including end
        all_days = trading_calendar.get_trading_days_between(
            start_date=end.replace(year=end.year - 1),
            end_date=end,
            include_start=True,
            include_end=True,
        )
        start_index = max(len(all_days) - args.days, 0)
        start = all_days[start_index]
    else:
        start = end

    portfolio_ids = [UUID(pid) for pid in args.portfolio] if args.portfolio else []

    return BackfillConfig(
        start=start,
        end=end,
        portfolio_ids=portfolio_ids,
        dry_run=args.dry_run,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recalculate NAV and equity balances for portfolios."
    )
    parser.add_argument(
        "--start",
        type=parse_iso_date,
        help="First trading day to process (YYYY-MM-DD). Defaults to end date.",
    )
    parser.add_argument(
        "--end",
        type=parse_iso_date,
        help="Last trading day to process (YYYY-MM-DD). Defaults to today or previous trading day.",
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Alternative to --start: number of recent trading days to process (including end date).",
    )
    parser.add_argument(
        "--portfolio",
        action="append",
        help="Portfolio UUID to backfill (may be supplied multiple times). Defaults to all active portfolios.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the work that would be performed without writing to the database.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = build_config(args)
    asyncio.run(backfill(config))


if __name__ == "__main__":
    main()
