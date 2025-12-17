#!/usr/bin/env python
"""
Monitor equity balances and P&L showing daily progression for each portfolio.

Shows one line per day per portfolio with:
- Starting Equity (equity at start of day)
- Daily P&L
- New Equity (equity at end of day)
- Gross Exposure
- Net Exposure

Usage:
    # Show all data
    python monitor_equity_pnl.py

    # Show data from Nov 20 to today
    python monitor_equity_pnl.py --start-date 2025-11-20

    # Show data for specific date range
    python monitor_equity_pnl.py --start-date 2025-11-20 --end-date 2025-11-25

    # Show specific portfolio
    python monitor_equity_pnl.py --portfolio <uuid> --start-date 2025-11-20
"""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import UUID

# Ensure backend package is importable when invoked directly
sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from app.core.db_utils import get_sync_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot


def show_daily_progression(
    portfolio_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Show daily progression for each portfolio.

    Args:
        portfolio_id: Optional portfolio UUID to filter
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)
    """

    with get_sync_session() as db:
        # Get portfolios
        portfolio_query = select(Portfolio.id, Portfolio.name, Portfolio.equity_balance)
        if portfolio_id:
            portfolio_query = portfolio_query.where(Portfolio.id == UUID(portfolio_id))

        portfolios_result = db.execute(portfolio_query)
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
            )

            # Apply date filters
            if start_date:
                snapshots_query = snapshots_query.where(PortfolioSnapshot.snapshot_date >= start_date)
            if end_date:
                snapshots_query = snapshots_query.where(PortfolioSnapshot.snapshot_date <= end_date)

            snapshots_query = snapshots_query.order_by(PortfolioSnapshot.snapshot_date)

            snapshots_result = db.execute(snapshots_query)
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

            # Summary statistics
            print()
            print(f"Total Snapshots: {len(snapshots)} trading days")

            if snapshots:
                # Calculate period summary
                first_equity = snapshots[0][1]  # equity_balance from first snapshot
                last_equity = snapshots[-1][1]   # equity_balance from last snapshot
                total_pnl = sum((s[2] or Decimal('0')) for s in snapshots)  # sum of daily_pnl
                first_date = snapshots[0][0]
                last_date = snapshots[-1][0]

                print()
                print("-" * 60)
                print(f"PERIOD SUMMARY ({first_date} to {last_date}):")
                print("-" * 60)
                print(f"  Starting Equity:  ${first_equity:>16,.2f}")
                print(f"  Ending Equity:    ${last_equity:>16,.2f}")
                print(f"  Total P&L:        ${total_pnl:>+16,.2f}")
                print(f"  Return:           {(last_equity - first_equity) / first_equity * 100:>+16.2f}%")
            print()


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


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
    parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Start date filter (YYYY-MM-DD format, e.g., 2025-11-20)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=date.today(),
        help="End date filter (YYYY-MM-DD format, defaults to today)",
    )
    args = parser.parse_args()

    # Print filter info
    if args.start_date or args.end_date != date.today():
        print(f"\nDate Filter: {args.start_date or 'beginning'} to {args.end_date}\n")

    try:
        show_daily_progression(
            portfolio_id=args.portfolio,
            start_date=args.start_date,
            end_date=args.end_date
        )
    except KeyboardInterrupt:
        print("\n\nStopped.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
