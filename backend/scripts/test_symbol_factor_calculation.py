"""
Test symbol factor calculation on Railway Core DB.

This script runs the symbol factor calculation for the current date
to verify the new architecture works correctly.
"""
import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Set up environment
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

from app.calculations.symbol_factors import (
    calculate_universe_factors,
    get_all_active_symbols,
    load_symbol_betas,
)
from app.database import AsyncSessionLocal


async def test_symbol_factors():
    """Test the symbol factor calculation."""
    print("=" * 60)
    print("TESTING SYMBOL FACTOR CALCULATION")
    print("=" * 60)

    # Use a recent trading day (Friday Dec 20, 2025 might be today)
    calculation_date = date.today()

    # If it's a weekend, use the previous Friday
    if calculation_date.weekday() == 5:  # Saturday
        calculation_date -= timedelta(days=1)
    elif calculation_date.weekday() == 6:  # Sunday
        calculation_date -= timedelta(days=2)

    print(f"\nCalculation date: {calculation_date}")

    # Step 1: Check what symbols we have
    print("\n--- Step 1: Getting active symbols ---")
    async with AsyncSessionLocal() as db:
        symbols = await get_all_active_symbols(db)
        print(f"Found {len(symbols)} unique PUBLIC equity symbols")
        if symbols:
            print(f"Sample symbols: {symbols[:10]}")

    if not symbols:
        print("No symbols found - cannot proceed with test")
        return

    # Step 2: Run the calculation (with a subset for testing)
    print("\n--- Step 2: Running universe factor calculation ---")
    print("(This may take a minute...)")

    result = await calculate_universe_factors(
        calculation_date=calculation_date,
        regularization_alpha=1.0,
        calculate_ridge=True,
        calculate_spread=True
    )

    print(f"\nResults:")
    print(f"  Symbols processed: {result['symbols_processed']}")
    print(f"  Ridge factors:")
    print(f"    - Calculated: {result['ridge_results']['calculated']}")
    print(f"    - From cache: {result['ridge_results']['cached']}")
    print(f"    - Failed: {result['ridge_results']['failed']}")
    print(f"  Spread factors:")
    print(f"    - Calculated: {result['spread_results']['calculated']}")
    print(f"    - From cache: {result['spread_results']['cached']}")
    print(f"    - Failed: {result['spread_results']['failed']}")

    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result['errors'][:5]:
            print(f"  - {error}")
        if len(result['errors']) > 5:
            print(f"  ... and {len(result['errors']) - 5} more")

    # Step 3: Verify we can load the calculated betas
    print("\n--- Step 3: Verifying stored betas ---")
    async with AsyncSessionLocal() as db:
        test_symbols = symbols[:5]
        betas = await load_symbol_betas(db, test_symbols, calculation_date)

        print(f"Loaded betas for {len(betas)} symbols:")
        for symbol, factors in list(betas.items())[:3]:
            print(f"  {symbol}:")
            for factor_name, beta_value in list(factors.items())[:4]:
                print(f"    - {factor_name}: {beta_value:.4f}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_symbol_factors())
