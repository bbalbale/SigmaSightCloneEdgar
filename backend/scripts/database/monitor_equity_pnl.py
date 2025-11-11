#!/usr/bin/env python
"""
Monitor equity balances and P&L showing daily progression for each portfolio.

Shows one line per day per portfolio with:
- Starting Equity (equity at start of day)
- Daily P&L
- New Equity (equity at end of day)
- Gross Exposure
- Net Exposure

For July 1 to Nov 7, 2025, you should see ~91 trading days per portfolio.
"""

import argparse
import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID

# Ensure backend package is importable when invoked directly
sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot


async def show_daily_progression(portfolio_id: Optional[str] = None):
    """Show daily progression for each portfolio."""

    async with get_async_session() as db:
        # Get portfolios
        portfolio_query = select(Portfolio.id, Portfolio.name, Portfolio.equity_balance)
        if portfolio_id:
            portfolio_query = portfolio_query.where(Portfolio.id == UUID(portfolio_id))

        portfolios_result = await db.execute(portfolio_query)
        portfolios = portfolios_result.all()

        if not portfolios:
            print("No portfolios found.")
            return

        for portfolio_id, portfolio_name, current_equity in portfolios:
            print()
            print("=" * 140)
            print(f"Portfolio: {portfolio_name}")
            print(f"Current Equity Balance in DB: ${current_equity:,.2f}")
            print("=" * 140)
            print()

            # Get all snapshots for this portfolio
            snapshots_query = (
                select(
                    PortfolioSnapshot.snapshot_date,
                    PortfolioSnapshot.equity_balance,
                    PortfolioSnapshot.daily_pnl,
                    PortfolioSnapshot.cumulative_pnl,
                    PortfolioSnapshot.gross_exposure,
                    PortfolioSnapshot.net_exposure,
                    PortfolioSnapshot.long_value,
                    PortfolioSnapshot.short_value,
                )
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date)
            )

            snapshots_result = await db.execute(snapshots_query)
            snapshots = snapshots_result.all()

            if not snapshots:
                print("  No snapshots found for this portfolio.")
                continue

            # Header
            print(f"{'Date':<12} | {'Start Equity':>16} | {'Daily P&L':>14} | {'End Equity':>16} | {'Gross Exp':>16} | {'Net Exp':>16} | {'Gross%':>8} | {'Long':>16} | {'Short':>16}")
            print("-" * 140)

            # First snapshot - starting equity is the entry value
            first_snapshot = snapshots[0]
            starting_equity = first_snapshot[1]  # equity_balance from first snapshot

            # Track previous equity for next iteration
            previous_equity = None

            for snapshot_date, end_equity, daily_pnl, cumulative_pnl, gross_exp, net_exp, long_val, short_val in snapshots:
                # For first day, start equity equals end equity (no previous day)
                if previous_equity is None:
                    start_equity = starting_equity
                    # Use cumulative_pnl as the initial P&L (captures entry to first snapshot)
                    display_pnl = cumulative_pnl or Decimal('0')
                else:
                    start_equity = previous_equity
                    display_pnl = daily_pnl or Decimal('0')

                # Calculate gross exposure as % of equity
                if end_equity and end_equity > 0:
                    gross_pct = (gross_exp / end_equity * 100) if gross_exp else Decimal('0')
                else:
                    gross_pct = Decimal('0')

                # Format values
                start_str = f"${start_equity:,.2f}" if start_equity else "N/A"
                pnl_str = f"${display_pnl:+,.2f}" if display_pnl else "$0.00"
                end_str = f"${end_equity:,.2f}" if end_equity else "N/A"
                gross_str = f"${gross_exp:,.2f}" if gross_exp else "N/A"
                net_str = f"${net_exp:,.2f}" if net_exp else "N/A"
                gross_pct_str = f"{gross_pct:.1f}%"
                long_str = f"${long_val:,.2f}" if long_val else "N/A"
                short_str = f"${short_val:,.2f}" if short_val else "N/A"

                print(
                    f"{snapshot_date} | "
                    f"{start_str:>16} | "
                    f"{pnl_str:>14} | "
                    f"{end_str:>16} | "
                    f"{gross_str:>16} | "
                    f"{net_str:>16} | "
                    f"{gross_pct_str:>8} | "
                    f"{long_str:>16} | "
                    f"{short_str:>16}"
                )

                # Update previous equity for next iteration
                previous_equity = end_equity

            print()
            print(f"Total Snapshots: {len(snapshots)} trading days")
            print()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Show daily equity progression for portfolios",
    )
    parser.add_argument(
        "--portfolio",
        type=str,
        help="Portfolio UUID to show (shows all if not specified)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(show_daily_progression(portfolio_id=args.portfolio))
    except KeyboardInterrupt:
        print("\n\nStopped.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
