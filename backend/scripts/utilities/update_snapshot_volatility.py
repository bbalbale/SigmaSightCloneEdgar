"""
Update existing portfolio snapshots with volatility data ONLY.

This is a focused script that only calculates and updates volatility fields,
without touching other snapshot fields that may have schema mismatches.
"""
import asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.calculations.volatility_analytics import calculate_portfolio_volatility


async def update_volatility_for_all_portfolios():
    """Update volatility data in existing snapshots."""
    async with get_async_session() as db:
        # Get all portfolios
        portfolio_result = await db.execute(select(Portfolio))
        portfolios = portfolio_result.scalars().all()

        print(f"\n{'='*80}")
        print(f"UPDATING VOLATILITY DATA - Found {len(portfolios)} portfolios")
        print(f"{'='*80}\n")

        today = date.today()
        total_success = 0
        total_failed = 0

        for portfolio in portfolios:
            print(f"\nProcessing: {portfolio.name}")
            print(f"Portfolio ID: {portfolio.id}")
            print(f"{'-'*80}")

            try:
                # Get latest snapshot for this portfolio
                snapshot_result = await db.execute(
                    select(PortfolioSnapshot)
                    .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                    .order_by(PortfolioSnapshot.snapshot_date.desc())
                    .limit(1)
                )
                snapshot = snapshot_result.scalar_one_or_none()

                if not snapshot:
                    print(f"[X] No snapshot found for portfolio")
                    total_failed += 1
                    continue

                print(f"[OK] Found snapshot: {snapshot.snapshot_date}")

                # Calculate volatility for this portfolio
                volatility_data = await calculate_portfolio_volatility(
                    db=db,
                    portfolio_id=portfolio.id,
                    calculation_date=snapshot.snapshot_date
                )

                if not volatility_data:
                    print(f"[X] Volatility calculation returned no data")
                    print(f"    Possible reasons:")
                    print(f"    - Insufficient price history (need 252+ days)")
                    print(f"    - No active positions")
                    print(f"    - Market data not available")
                    total_failed += 1
                    continue

                # Update ONLY the volatility fields
                def to_decimal(value):
                    return Decimal(str(value)) if value is not None else None

                snapshot.realized_volatility_21d = to_decimal(volatility_data.get('realized_vol_21d'))
                snapshot.realized_volatility_63d = to_decimal(volatility_data.get('realized_vol_63d'))
                snapshot.expected_volatility_21d = to_decimal(volatility_data.get('expected_vol_21d'))
                snapshot.volatility_trend = volatility_data.get('vol_trend')
                snapshot.volatility_percentile = to_decimal(volatility_data.get('vol_percentile'))

                await db.commit()

                # Display results
                if snapshot.realized_volatility_21d is not None:
                    print(f"[OK] Volatility updated successfully:")
                    print(f"     21-day: {snapshot.realized_volatility_21d:.4f} ({snapshot.realized_volatility_21d * 100:.2f}%)")
                    if snapshot.realized_volatility_63d is not None:
                        print(f"     63-day: {snapshot.realized_volatility_63d:.4f} ({snapshot.realized_volatility_63d * 100:.2f}%)")
                    if snapshot.expected_volatility_21d is not None:
                        print(f"     Expected: {snapshot.expected_volatility_21d:.4f} ({snapshot.expected_volatility_21d * 100:.2f}%)")
                    if snapshot.volatility_trend:
                        print(f"     Trend: {snapshot.volatility_trend}")
                    if snapshot.volatility_percentile is not None:
                        print(f"     Percentile: {snapshot.volatility_percentile:.4f} ({snapshot.volatility_percentile * 100:.1f}th)")
                    total_success += 1
                else:
                    print(f"[!] Volatility calculation incomplete")
                    total_failed += 1

            except Exception as e:
                print(f"[X] Error: {str(e)}")
                await db.rollback()
                total_failed += 1

        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total portfolios: {len(portfolios)}")
        print(f"Successful volatility updates: {total_success}")
        print(f"Failed: {total_failed}")

        if total_success > 0:
            print(f"\n[OK] Volatility data successfully populated!")
            print(f"\nNEXT STEPS:")
            print(f"  1. Refresh the frontend risk metrics page")
            print(f"  2. Volatility analysis should now display")
        elif total_failed == len(portfolios):
            print(f"\n[X] ALL PORTFOLIOS FAILED")
            print(f"\nPOSSIBLE REASONS:")
            print(f"  1. Insufficient price data (need 252+ days of history)")
            print(f"  2. Market data not loaded in database")
            print(f"  3. Private assets without price history")
            print(f"\nRECOMMENDATION:")
            print(f"  Check that public equities (AAPL, MSFT, etc.) have price")
            print(f"  history in the market_data_cache table")
        else:
            print(f"\n[!] PARTIAL SUCCESS")
            print(f"  Some portfolios succeeded, others failed.")
            print(f"  Check logs above for details.")

        print()


if __name__ == "__main__":
    asyncio.run(update_volatility_for_all_portfolios())
