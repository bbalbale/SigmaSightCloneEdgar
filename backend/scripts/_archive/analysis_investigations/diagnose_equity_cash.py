#!/usr/bin/env python
"""
Diagnose equity, cash, and position mark alignment for portfolios.

This tool compares:
  * Portfolio.equity_balance
  * PortfolioSnapshot.net_asset_value / cash_value
  * Sum(Position.market_value) for active positions

Usage:
    python -m scripts.analysis.diagnose_equity_cash
    python -m scripts.analysis.diagnose_equity_cash --date 2025-11-07
    python -m scripts.analysis.diagnose_equity_cash --portfolio <UUID> --threshold 5
"""

import argparse
import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Iterable, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio


DecimalZero = Decimal("0")


def parse_date(value: Optional[str]) -> date:
    if value:
        return datetime.strptime(value, "%Y-%m-%d").date()
    return date.today()


def parse_portfolios(values: Optional[Iterable[str]]) -> Optional[Tuple[UUID, ...]]:
    if not values:
        return None
    parsed: list[UUID] = []
    for item in values:
        try:
            parsed.append(UUID(item))
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid UUID: {item}") from None
    return tuple(parsed)


async def load_portfolios(
    session: AsyncSession,
    portfolio_filter: Optional[Tuple[UUID, ...]],
) -> Dict[UUID, Portfolio]:
    query = select(Portfolio).where(Portfolio.deleted_at.is_(None))
    if portfolio_filter:
        query = query.where(Portfolio.id.in_(portfolio_filter))
    result = await session.execute(query)
    portfolios = result.scalars().all()
    return {portfolio.id: portfolio for portfolio in portfolios}


async def load_snapshots(
    session: AsyncSession,
    calc_date: date,
    portfolio_filter: Optional[Tuple[UUID, ...]],
) -> Dict[UUID, PortfolioSnapshot]:
    query = select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == calc_date)
    if portfolio_filter:
        query = query.where(PortfolioSnapshot.portfolio_id.in_(portfolio_filter))
    result = await session.execute(query)
    snapshots = result.scalars().all()
    return {snapshot.portfolio_id: snapshot for snapshot in snapshots}


async def load_position_summaries(
    session: AsyncSession,
    calc_date: date,
    portfolio_filter: Optional[Tuple[UUID, ...]],
) -> Dict[UUID, Tuple[Decimal, int]]:
    query = (
        select(
            Position.portfolio_id,
            func.coalesce(func.sum(Position.market_value), 0),
            func.count(),
        )
        .where(
            and_(
                Position.deleted_at.is_(None),
                Position.entry_date <= calc_date,
                or_(
                    Position.exit_date.is_(None),
                    Position.exit_date >= calc_date,
                ),
            )
        )
        .group_by(Position.portfolio_id)
    )

    if portfolio_filter:
        query = query.where(Position.portfolio_id.in_(portfolio_filter))

    result = await session.execute(query)
    summaries: Dict[UUID, Tuple[Decimal, int]] = {}
    for portfolio_id, gross_value, position_count in result:
        value_decimal = Decimal(str(gross_value or 0))
        summaries[portfolio_id] = (value_decimal, int(position_count or 0))
    return summaries


def format_money(amount: Optional[Decimal]) -> str:
    if amount is None:
        return "N/A"
    return f"${amount:,.2f}"


def summarize_portfolio(
    portfolio: Portfolio,
    snapshot: Optional[PortfolioSnapshot],
    position_summary: Tuple[Decimal, int],
    threshold: Decimal,
) -> Tuple[bool, str, str]:
    positions_value, position_count = position_summary
    equity_balance = portfolio.equity_balance or DecimalZero

    nav = snapshot.net_asset_value if snapshot else None
    cash = snapshot.cash_value if snapshot else None
    long_value = snapshot.long_value if snapshot else None
    short_value = snapshot.short_value if snapshot else None

    derived_cash = equity_balance - positions_value
    nav_vs_positions = None
    equity_vs_nav = None
    cash_vs_derived = None

    if nav is not None:
        nav_vs_positions = nav - positions_value
        equity_vs_nav = equity_balance - nav

    if cash is not None:
        cash_vs_derived = cash - derived_cash

    flagged = any(
        abs(metric) > threshold
        for metric in (nav_vs_positions, equity_vs_nav, cash_vs_derived)
        if metric is not None
    )

    lines = [
        f"{'[FLAG]' if flagged else '[ OK ]'} {portfolio.name} ({portfolio.id})",
        f"  Equity balance:      {format_money(equity_balance)}",
        f"  Snapshot NAV:        {format_money(nav)}",
        f"  Sum(position MV):    {format_money(positions_value)} (positions: {position_count})",
        f"  Snapshot cash:       {format_money(cash)}",
        f"  Derived cash:        {format_money(derived_cash)}",
    ]

    if long_value is not None and short_value is not None:
        lines.append(
            f"  Snapshot exposure:   long={format_money(long_value)} short={format_money(short_value)}"
        )

    lines.append(f"  NAV vs positions:   {format_money(nav_vs_positions)}")
    lines.append(f"  Equity vs NAV:      {format_money(equity_vs_nav)}")
    lines.append(f"  Cash vs derived:    {format_money(cash_vs_derived)}")

    if snapshot is None:
        lines.append("  WARNING: No snapshot found for calculation date.")

    return flagged, "\n".join(lines), portfolio.name


async def run_diagnostic(
    calc_date: date,
    portfolio_ids: Optional[Tuple[UUID, ...]],
    threshold: Decimal,
) -> None:
    async with AsyncSessionLocal() as session:
        portfolios = await load_portfolios(session, portfolio_ids)

        if not portfolios:
            print("No active portfolios matched the filter.")
            return

        snapshots = await load_snapshots(session, calc_date, portfolio_ids)
        positions = await load_position_summaries(session, calc_date, portfolio_ids)

    print(
        f"=== Equity & Cash Diagnostic for {calc_date.isoformat()} "
        f"(threshold={format_money(threshold)}) ==="
    )

    flagged = 0
    results = []

    for portfolio_id, portfolio in portfolios.items():
        snapshot = snapshots.get(portfolio_id)
        position_summary = positions.get(portfolio_id, (DecimalZero, 0))
        is_flagged, report, name = summarize_portfolio(
            portfolio,
            snapshot,
            position_summary,
            threshold,
        )
        flagged += int(is_flagged)
        results.append((is_flagged, name.lower(), report))

    # Flagged entries first, then alphabetical
    for _, _, report in sorted(results, key=lambda item: (not item[0], item[1])):
        print()
        print(report)

    print()
    print(f"Flagged portfolios: {flagged} / {len(results)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose equity vs cash vs position marks.")
    parser.add_argument("--date", help="Calculation date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument(
        "--portfolio",
        action="append",
        help="Portfolio UUID to include (can be specified multiple times).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="Dollar threshold for flagging differences (default: 1.0).",
    )

    args = parser.parse_args()

    calc_date = parse_date(args.date)
    portfolio_ids = parse_portfolios(args.portfolio)
    threshold = Decimal(str(args.threshold))

    asyncio.run(run_diagnostic(calc_date, portfolio_ids, threshold))


if __name__ == "__main__":
    main()
