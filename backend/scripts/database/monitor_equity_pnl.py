#!/usr/bin/env python
"""
Monitor equity balances and P&L as portfolio snapshots are being created.

This script continuously monitors portfolio snapshots in the database and displays
daily updates showing the latest equity balance, daily P&L, and cumulative P&L
for each portfolio during batch processing.

Display Format:
    - One line per portfolio showing the most recent snapshot
    - Starting Equity: First snapshot equity balance
    - Current Equity: Latest snapshot equity balance
    - Daily P&L: P&L for the current day
    - Cumulative P&L: Total P&L from start to current date
    - Days: Total number of snapshots (trading days)

Usage:
    python monitor_equity_pnl.py                    # Monitor all portfolios (default: 3s refresh)
    python monitor_equity_pnl.py --portfolio <uuid> # Monitor specific portfolio
    python monitor_equity_pnl.py --interval 5       # Custom refresh interval (seconds)
"""

import argparse
import asyncio
import sys
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import UUID

# Configure UTF-8 output handling for Windows terminals
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")  # type: ignore[attr-defined]
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")  # type: ignore[attr-defined]

# Ensure backend package is importable when invoked directly
sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, func, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.core.logging import get_logger

logger = get_logger(__name__)


class EquityMonitor:
    """Monitor equity balances across portfolio snapshots."""

    def __init__(self, portfolio_id: Optional[str] = None, interval: int = 3):
        self.portfolio_id = UUID(portfolio_id) if portfolio_id else None
        self.interval = interval
        self.last_snapshot_counts: Dict[UUID, int] = {}
        self.last_snapshot_dates: Dict[UUID, date] = {}
        self.portfolio_names: Dict[UUID, str] = {}
        self.starting_equity: Dict[UUID, Optional[Decimal]] = {}

    async def get_portfolio_names(self) -> None:
        """Fetch portfolio names for display."""
        async with get_async_session() as db:
            query = select(Portfolio.id, Portfolio.name)
            if self.portfolio_id:
                query = query.where(Portfolio.id == self.portfolio_id)

            result = await db.execute(query)
            portfolios = result.all()

            for portfolio_id, name in portfolios:
                self.portfolio_names[portfolio_id] = name

    async def get_snapshot_data(self) -> Dict[UUID, List[Tuple[date, Optional[Decimal], Optional[Decimal], Optional[Decimal]]]]:
        """
        Get snapshot data for each portfolio.

        Returns:
            Dict mapping portfolio_id to list of (snapshot_date, equity_balance, daily_pnl, cumulative_pnl) tuples
        """
        async with get_async_session() as db:
            query = (
                select(
                    PortfolioSnapshot.portfolio_id,
                    PortfolioSnapshot.snapshot_date,
                    PortfolioSnapshot.equity_balance,
                    PortfolioSnapshot.daily_pnl,
                    PortfolioSnapshot.cumulative_pnl,
                    PortfolioSnapshot.net_asset_value,
                )
                .order_by(
                    PortfolioSnapshot.portfolio_id,
                    PortfolioSnapshot.snapshot_date
                )
            )

            if self.portfolio_id:
                query = query.where(PortfolioSnapshot.portfolio_id == self.portfolio_id)

            result = await db.execute(query)
            rows = result.all()

            # Group by portfolio_id
            portfolio_data: Dict[UUID, List[Tuple[date, Optional[Decimal], Optional[Decimal], Optional[Decimal]]]] = {}
            for portfolio_id, snapshot_date, equity_balance, daily_pnl, cumulative_pnl, nav in rows:
                if portfolio_id not in portfolio_data:
                    portfolio_data[portfolio_id] = []
                portfolio_data[portfolio_id].append((snapshot_date, equity_balance, daily_pnl, cumulative_pnl))

            return portfolio_data

    def format_currency(self, value: Optional[Decimal]) -> str:
        """Format currency values for display."""
        if value is None:
            return "N/A".rjust(15)
        return f"${value:,.2f}".rjust(15)

    def format_pnl(self, value: Optional[Decimal]) -> str:
        """Format P&L values with color indicators."""
        if value is None:
            return "N/A".rjust(15)

        formatted = f"${value:,.2f}".rjust(15)
        if value > 0:
            return f"+{formatted}"
        return formatted

    def display_snapshot_summary(self, portfolio_data: Dict[UUID, List[Tuple]]) -> None:
        """Display current snapshot summary with daily updates."""
        # Clear screen (cross-platform)
        print("\033[2J\033[H", end="")

        print("=" * 120)
        print(f"EQUITY & P&L DAILY TRACKER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 120)
        print()

        if not portfolio_data:
            print("No portfolio snapshots found.")
            return

        # Table header
        print(f"{'Portfolio':40} | {'Date':12} | {'Starting Equity':>16} | {'Current Equity':>16} | {'Daily P&L':>15} | {'Cumulative P&L':>15} | {'Days':>5}")
        print("-" * 120)

        for portfolio_id, snapshots in sorted(portfolio_data.items(), key=lambda x: self.portfolio_names.get(x[0], "")):
            if not snapshots:
                continue

            portfolio_name = self.portfolio_names.get(portfolio_id, str(portfolio_id))[:40]
            current_count = len(snapshots)
            previous_count = self.last_snapshot_counts.get(portfolio_id, 0)

            # Get latest snapshot
            latest_date, latest_equity, latest_daily_pnl, latest_cumulative_pnl = snapshots[-1]

            # Track starting equity (first snapshot equity)
            if portfolio_id not in self.starting_equity:
                first_equity = snapshots[0][1]  # equity_balance from first snapshot
                self.starting_equity[portfolio_id] = first_equity

            starting_equity = self.starting_equity[portfolio_id]

            # Check if this is a new day (date changed)
            previous_date = self.last_snapshot_dates.get(portfolio_id)
            is_new_day = previous_date != latest_date

            # Status indicator
            if is_new_day:
                status = "NEW DAY"
            elif current_count > previous_count:
                status = "UPDATED"
            else:
                status = ""

            # Color coding for daily P&L
            if latest_daily_pnl and latest_daily_pnl > 0:
                daily_pnl_str = f"+{self.format_currency(latest_daily_pnl).strip()}"
            else:
                daily_pnl_str = self.format_currency(latest_daily_pnl).strip()

            # Color coding for cumulative P&L
            if latest_cumulative_pnl and latest_cumulative_pnl > 0:
                cumulative_pnl_str = f"+{self.format_currency(latest_cumulative_pnl).strip()}"
            else:
                cumulative_pnl_str = self.format_currency(latest_cumulative_pnl).strip()

            print(
                f"{portfolio_name:40} | "
                f"{latest_date.strftime('%Y-%m-%d'):12} | "
                f"{self.format_currency(starting_equity)} | "
                f"{self.format_currency(latest_equity)} | "
                f"{daily_pnl_str:>15} | "
                f"{cumulative_pnl_str:>15} | "
                f"{current_count:>5}"
            )

            if status:
                print(f"  [{status}]")

            # Update tracking
            self.last_snapshot_counts[portfolio_id] = current_count
            self.last_snapshot_dates[portfolio_id] = latest_date

        print()
        print("=" * 120)
        print(f"Refreshing every {self.interval} seconds... (Ctrl+C to stop)")
        print("=" * 120)

    async def monitor_loop(self) -> None:
        """Main monitoring loop."""
        print("Starting equity monitor...")
        print(f"Refresh interval: {self.interval} seconds")
        if self.portfolio_id:
            print(f"Monitoring portfolio: {self.portfolio_id}")
        else:
            print("Monitoring all portfolios")
        print()

        # Load portfolio names
        await self.get_portfolio_names()

        try:
            while True:
                portfolio_data = await self.get_snapshot_data()
                self.display_snapshot_summary(portfolio_data)
                await asyncio.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
        except Exception as e:
            logger.error(f"Error during monitoring: {e}", exc_info=True)
            print(f"\nError: {e}")

    async def run(self) -> None:
        """Run the monitor."""
        await self.monitor_loop()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor portfolio equity balances and P&L during batch processing",
    )
    parser.add_argument(
        "--portfolio",
        type=str,
        help="Portfolio UUID to monitor (monitors all if not specified)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3,
        help="Refresh interval in seconds (default: 3)",
    )
    args = parser.parse_args()

    monitor = EquityMonitor(
        portfolio_id=args.portfolio,
        interval=args.interval,
    )

    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
