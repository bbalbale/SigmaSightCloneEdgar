"""
Test portfolio factor service on Railway.

This script tests the portfolio factor aggregation using
pre-computed symbol betas.
"""
import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Set up environment
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.services.portfolio_factor_service import (
    get_portfolio_factor_exposures,
    get_portfolio_positions_with_weights,
    calculate_and_store_portfolio_factors,
    compare_symbol_vs_position_factors,
)


async def test_portfolio_factors():
    """Test portfolio factor aggregation."""
    print("=" * 60)
    print("TESTING PORTFOLIO FACTOR SERVICE")
    print("=" * 60)

    # Use same date as symbol calculation
    calculation_date = date(2025, 12, 19)
    print(f"\nCalculation date: {calculation_date}")

    # Get a portfolio to test with
    async with AsyncSessionLocal() as db:
        portfolio_stmt = select(Portfolio).limit(3)
        result = await db.execute(portfolio_stmt)
        portfolios = result.scalars().all()

        if not portfolios:
            print("No portfolios found!")
            return

        print(f"\nFound {len(portfolios)} portfolios:")
        for p in portfolios:
            print(f"  - {p.id}: {p.name} (equity=${float(p.equity_balance):,.2f})")

    # Test each portfolio
    for portfolio in portfolios:
        print(f"\n{'='*60}")
        print(f"PORTFOLIO: {portfolio.name}")
        print("=" * 60)

        async with AsyncSessionLocal() as db:
            # Step 1: Get positions with weights
            print("\n--- Step 1: Loading positions with weights ---")
            try:
                position_weights, equity = await get_portfolio_positions_with_weights(
                    db, portfolio.id
                )
                print(f"Loaded {len(position_weights)} positions, equity=${equity:,.2f}")

                # Show sample weights
                for pw in position_weights[:5]:
                    delta_str = f", delta={pw.delta:.2f}" if pw.delta else ""
                    print(f"  {pw.symbol:6}: weight={pw.weight:7.4f} ({pw.weight*100:5.2f}%){delta_str}")
                if len(position_weights) > 5:
                    print(f"  ... and {len(position_weights) - 5} more")

            except Exception as e:
                print(f"Error loading positions: {e}")
                continue

            # Step 2: Get factor exposures (lookup + aggregate)
            print("\n--- Step 2: Getting portfolio factor exposures ---")
            try:
                result = await get_portfolio_factor_exposures(
                    db=db,
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date,
                    use_delta_adjusted=False,
                    include_ridge=True,
                    include_spread=True
                )

                print(f"\nData Quality:")
                print(f"  Symbols with Ridge betas: {result['data_quality']['symbols_with_ridge']}")
                print(f"  Symbols with Spread betas: {result['data_quality']['symbols_with_spread']}")
                print(f"  Symbols missing: {result['data_quality']['symbols_missing']}")

                print(f"\nRidge Factor Betas:")
                for factor, beta in sorted(result['ridge_betas'].items()):
                    print(f"  {factor:15}: {beta:8.4f}")

                print(f"\nSpread Factor Betas:")
                for factor, beta in sorted(result['spread_betas'].items()):
                    print(f"  {factor:25}: {beta:8.4f}")

            except Exception as e:
                print(f"Error getting factor exposures: {e}")
                import traceback
                traceback.print_exc()
                continue

            # Step 3: Store to database
            print("\n--- Step 3: Storing portfolio factor exposures ---")
            try:
                store_result = await calculate_and_store_portfolio_factors(
                    db=db,
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date,
                    use_delta_adjusted=False
                )
                print(f"Stored {store_result.get('storage_results', {}).get('records_stored', 0)} records")

            except Exception as e:
                print(f"Error storing: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_portfolio_factors())
