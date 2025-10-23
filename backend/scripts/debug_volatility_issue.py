"""
Diagnostic script for volatility metrics issue

Checks:
1. Portfolio snapshots existence
2. Volatility field population in snapshots
3. Historical price data availability
4. Position returns calculation feasibility
"""

import asyncio
from datetime import date, timedelta
from sqlalchemy import select, func, and_
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.models.users import Portfolio
from uuid import UUID


async def diagnose_volatility_issue():
    """Run comprehensive diagnostics on volatility calculation"""

    print("=" * 80)
    print("VOLATILITY METRICS DIAGNOSTIC REPORT")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # Get all portfolios
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = portfolios_result.scalars().all()

        if not portfolios:
            print("[ERROR] No portfolios found in database!")
            return

        print(f"[INFO] Found {len(portfolios)} portfolio(s) in database")
        print()

        for portfolio in portfolios:
            print("-" * 80)
            print(f"Portfolio: {portfolio.name}")
            print(f"ID: {portfolio.id}")
            print(f"User ID: {portfolio.user_id}")
            print("-" * 80)

            # Check 1: Snapshot existence
            print("\n[CHECK 1] Snapshot Existence")
            print("-" * 40)

            snapshot_query = select(PortfolioSnapshot).where(
                PortfolioSnapshot.portfolio_id == portfolio.id
            ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(10)

            snapshot_result = await db.execute(snapshot_query)
            snapshots = snapshot_result.scalars().all()

            if not snapshots:
                print("[ERROR] No snapshots found for this portfolio!")
                print("   -> Need to run batch processing to create snapshots")
                continue

            print(f"[OK] Found {len(snapshots)} snapshot(s)")
            print(f"   Latest snapshot date: {snapshots[0].snapshot_date}")
            print(f"   Oldest snapshot date: {snapshots[-1].snapshot_date}")

            # Check 2: Volatility field population
            print("\n[CHECK 2] Volatility Field Population")
            print("-" * 40)

            latest_snapshot = snapshots[0]
            vol_fields = {
                'realized_volatility_21d': latest_snapshot.realized_volatility_21d,
                'realized_volatility_63d': latest_snapshot.realized_volatility_63d,
                'expected_volatility_21d': latest_snapshot.expected_volatility_21d,
                'volatility_trend': latest_snapshot.volatility_trend,
                'volatility_percentile': latest_snapshot.volatility_percentile
            }

            all_null = all(v is None for v in vol_fields.values())

            if all_null:
                print("[ERROR] All volatility fields are NULL in latest snapshot!")
                print("   -> Volatility calculation failed or hasn't run")
            else:
                print("[OK] Some volatility fields are populated:")
                for field, value in vol_fields.items():
                    if value is not None:
                        if field == 'volatility_trend':
                            print(f"   {field}: {value}")
                        else:
                            print(f"   {field}: {float(value):.4f}")
                    else:
                        print(f"   {field}: NULL [ERROR]")

            # Check 3: Active positions
            print("\n[CHECK 3] Active Positions")
            print("-" * 40)

            positions_query = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.exit_date.is_(None)
                )
            )

            positions_result = await db.execute(positions_query)
            positions = positions_result.scalars().all()

            if not positions:
                print("[ERROR] No active positions found!")
                continue

            print(f"[OK] Found {len(positions)} active position(s)")

            # Check 4: Historical price data
            print("\n[CHECK 4] Historical Price Data Availability")
            print("-" * 40)

            today = date.today()
            lookback_date = today - timedelta(days=90)  # Need 63+ days

            positions_with_data = 0
            positions_without_data = 0

            for position in positions[:10]:  # Check first 10 positions
                # For options, use underlying symbol
                symbol = position.underlying_symbol if position.underlying_symbol else position.symbol

                price_count_query = select(func.count(MarketDataCache.id)).where(
                    and_(
                        MarketDataCache.symbol == symbol,
                        MarketDataCache.price_date >= lookback_date,
                        MarketDataCache.price_date <= today,
                        MarketDataCache.close_price.isnot(None)
                    )
                )

                count_result = await db.execute(price_count_query)
                price_count = count_result.scalar()

                if price_count >= 63:
                    positions_with_data += 1
                    print(f"   [OK] {symbol}: {price_count} days of data")
                else:
                    positions_without_data += 1
                    print(f"   [ERROR] {symbol}: {price_count} days of data (need 63+)")

            if len(positions) > 10:
                print(f"   ... and {len(positions) - 10} more positions")

            # Summary
            print("\n[SUMMARY]")
            print("-" * 40)

            if all_null:
                print("[ERROR] ISSUE IDENTIFIED: Volatility fields are NULL")
                print("\nPossible causes:")
                print("1. Insufficient historical price data (need 63+ days)")
                print("2. Volatility calculation failed during snapshot creation")
                print("3. Positions lack underlying price data (for options)")
                print("\nRecommended fix:")
                print("- Check backend logs for errors during snapshot creation")
                if positions_without_data > 0:
                    print(f"- Fetch missing price data for {positions_without_data} positions")
                print("- Re-run snapshot creation for this portfolio")
            else:
                missing_fields = [k for k, v in vol_fields.items() if v is None]
                if missing_fields:
                    print(f"[WARNING] PARTIAL DATA: {len(missing_fields)} field(s) are NULL:")
                    for field in missing_fields:
                        print(f"   - {field}")
                else:
                    print("[OK] All volatility fields are populated!")

            print()


if __name__ == "__main__":
    asyncio.run(diagnose_volatility_issue())
