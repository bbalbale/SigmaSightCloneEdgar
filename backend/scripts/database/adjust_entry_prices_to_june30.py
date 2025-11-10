#!/usr/bin/env python
"""
Adjust Entry Prices to June 30, 2025

This script adjusts all PUBLIC stock entry prices to match their June 30, 2025
closing prices. This ensures the first tracking day (July 1, 2025) starts with
zero P&L, making debugging easier.

Usage:
    python adjust_entry_prices_to_june30.py --dry-run  # Preview changes
    python adjust_entry_prices_to_june30.py --confirm  # Apply changes
"""

import argparse
import asyncio
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)

from sqlalchemy import select, update
import yfinance as yf

from app.database import get_async_session
from app.models.positions import Position
from app.models.users import Portfolio
from app.core.logging import get_logger

logger = get_logger(__name__)

TARGET_DATE = date(2025, 6, 30)


def fetch_june30_prices(symbols: list[str]) -> Dict[str, Optional[Decimal]]:
    """
    Fetch June 30, 2025 closing prices for all symbols using yfinance.

    Returns:
        Dict mapping symbol to closing price (or None if unavailable)
    """
    prices = {}

    print(f"\nFetching June 30, 2025 prices for {len(symbols)} symbols...")
    print("-" * 80)

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            # Get data around June 30, 2025
            hist = ticker.history(start="2025-06-27", end="2025-07-02")

            if hist.empty:
                print(f"  {symbol:10} - No data available")
                prices[symbol] = None
                continue

            # Try to get June 30 close, or the closest date before it
            if TARGET_DATE in hist.index.date:
                close_price = hist.loc[hist.index.date == TARGET_DATE, 'Close'].iloc[0]
            else:
                # Get the last available date before July 1
                close_price = hist['Close'].iloc[-1]

            prices[symbol] = Decimal(str(round(close_price, 2)))
            print(f"  {symbol:10} - ${prices[symbol]:>10,.2f}")

        except Exception as e:
            print(f"  {symbol:10} - Error: {e}")
            prices[symbol] = None

    print("-" * 80)
    return prices


async def adjust_entry_prices(dry_run: bool, confirm: bool) -> None:
    """
    Adjust entry prices for all PUBLIC positions to June 30, 2025 prices.
    """
    if not dry_run and not confirm:
        print("ERROR: This operation modifies position data. Use --confirm to proceed.")
        print("To preview changes, run with --dry-run.")
        return

    print("=" * 80)
    print("ADJUST ENTRY PRICES TO JUNE 30, 2025")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify data)'}")
    print()

    async with get_async_session() as db:
        # Get all PUBLIC positions (exclude OPTIONS and PRIVATE)
        result = await db.execute(
            select(Position, Portfolio.name)
            .join(Portfolio, Position.portfolio_id == Portfolio.id)
            .where(Position.investment_class == 'PUBLIC')
            .order_by(Portfolio.name, Position.symbol)
        )
        positions = result.all()

        if not positions:
            print("No PUBLIC positions found.")
            return

        print(f"Found {len(positions)} PUBLIC positions to adjust")
        print()

        # Get unique symbols
        unique_symbols = sorted(list(set(pos.symbol for pos, _ in positions)))
        print(f"Unique symbols: {len(unique_symbols)}")

        # Fetch June 30 prices
        june30_prices = fetch_june30_prices(unique_symbols)

        # Calculate adjustments
        print("\n" + "=" * 80)
        print("POSITION ADJUSTMENTS")
        print("=" * 80)
        print(f"{'Portfolio':40} | {'Symbol':8} | {'Old Entry':>12} | {'New Entry':>12} | {'Adjustment':>12}")
        print("-" * 80)

        adjustments_made = 0
        adjustments_skipped = 0
        total_positions = 0

        for position, portfolio_name in positions:
            total_positions += 1
            symbol = position.symbol
            old_entry = position.entry_price
            new_entry = june30_prices.get(symbol)

            if new_entry is None:
                print(f"{portfolio_name[:40]:40} | {symbol:8} | ${old_entry:>10,.2f} | {'N/A':>12} | SKIPPED")
                adjustments_skipped += 1
                continue

            adjustment = new_entry - old_entry
            adjustment_pct = (adjustment / old_entry * 100) if old_entry else 0

            print(
                f"{portfolio_name[:40]:40} | {symbol:8} | "
                f"${old_entry:>10,.2f} | ${new_entry:>10,.2f} | "
                f"{'+' if adjustment >= 0 else ''}{adjustment:>10,.2f} ({adjustment_pct:>+6.2f}%)"
            )

            # Apply change if not dry run
            if not dry_run:
                position.entry_price = new_entry
                db.add(position)

            adjustments_made += 1

        print("-" * 80)
        print(f"Total positions: {total_positions}")
        print(f"Adjustments to apply: {adjustments_made}")
        print(f"Skipped (no price data): {adjustments_skipped}")
        print()

        # Commit or rollback
        if not dry_run:
            print("Committing changes...")
            await db.commit()
            print("[OK] Changes committed successfully!")
        else:
            print("Rolling back (dry run mode)...")
            await db.rollback()
            print("[OK] Dry run complete - no changes made")

        print()
        print("=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        if dry_run:
            print("1. Review the adjustments above")
            print("2. Run with --confirm to apply changes")
            print("3. After applying, update Ben Mock Portfolios.md")
            print("4. Update seed_demo_portfolios.py with new entry prices")
        else:
            print("[OK] Entry prices updated in database")
            print()
            print("Manual updates still needed:")
            print("1. Update entry_price values in seed_demo_portfolios.py")
            print("2. Update entry prices in Ben Mock Portfolios.md (documentation)")
            print()
            print("After manual updates, positions table and seed data will be in sync.")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Adjust entry prices to June 30, 2025 closing prices",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying data",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm and apply changes to the database",
    )
    args = parser.parse_args()

    asyncio.run(adjust_entry_prices(args.dry_run, args.confirm))


if __name__ == "__main__":
    main()
