#!/usr/bin/env python3
"""
Comprehensive database state verification for Railway

Shows complete picture of:
- All positions by portfolio
- Historical price data coverage per position
- Calculation results (Greeks, factors, correlations)
- Data gaps and completeness

Usage:
  uv run python scripts/verification/verify_database_state.py
"""
import os
import asyncio
from sqlalchemy import select, func, desc
from datetime import datetime

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.market_data import PositionGreeks, PositionFactorExposure
from app.models.correlations import CorrelationCalculation
from app.models.snapshots import PortfolioSnapshot
from app.models.history import HistoricalPrice


async def verify_database_state():
    """Comprehensive database state verification."""
    print("=" * 80)
    print("COMPREHENSIVE DATABASE STATE REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    async with get_async_session() as db:
        # Get all portfolios
        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()

        print(f"📊 Total Portfolios: {len(portfolios)}")
        print("")

        for portfolio in portfolios:
            print("=" * 80)
            print(f"PORTFOLIO: {portfolio.name}")
            print(f"ID: {portfolio.id}")
            print("=" * 80)
            print("")

            # Get positions for this portfolio
            result = await db.execute(
                select(Position)
                .where(Position.portfolio_id == portfolio.id)
                .order_by(Position.symbol)
            )
            positions = result.scalars().all()

            print(f"📈 Positions: {len(positions)}")
            print("")

            for i, position in enumerate(positions, 1):
                print(f"{i}. {position.symbol} ({position.position_type.value})")
                print(f"   Quantity: {position.quantity:,.2f}")
                if position.entry_price:
                    print(f"   Entry Price: ${position.entry_price:,.2f}")
                print(f"   Entry Date: {position.entry_date}")

                # Check historical price data
                result = await db.execute(
                    select(
                        func.count(HistoricalPrice.id),
                        func.min(HistoricalPrice.date),
                        func.max(HistoricalPrice.date)
                    )
                    .where(HistoricalPrice.symbol == position.symbol)
                )
                price_count, min_date, max_date = result.one()

                if price_count > 0:
                    days_range = (max_date - min_date).days + 1 if max_date and min_date else 0
                    print(f"   📊 Historical Prices: {price_count} records")
                    print(f"      Range: {min_date} to {max_date} ({days_range} days)")
                else:
                    print(f"   ❌ Historical Prices: No data")

                # Check Greeks (options only)
                if position.position_type.value in ['CALL', 'PUT']:
                    result = await db.execute(
                        select(
                            func.count(PositionGreeks.id),
                            func.max(PositionGreeks.calculation_date)
                        )
                        .where(PositionGreeks.position_id == position.id)
                    )
                    greeks_count, latest_greeks = result.one()

                    if greeks_count > 0:
                        print(f"   ✅ Greeks: {greeks_count} records (latest: {latest_greeks})")
                    else:
                        print(f"   ❌ Greeks: No calculations")

                # Check Factor Exposures
                result = await db.execute(
                    select(
                        func.count(PositionFactorExposure.id),
                        func.max(PositionFactorExposure.calculation_date)
                    )
                    .where(PositionFactorExposure.position_id == position.id)
                )
                factor_count, latest_factor = result.one()

                if factor_count > 0:
                    print(f"   ✅ Factor Exposures: {factor_count} records (latest: {latest_factor})")
                else:
                    print(f"   ❌ Factor Exposures: No calculations")

                print("")

            # Portfolio-level calculations
            print("-" * 80)
            print("PORTFOLIO-LEVEL CALCULATIONS")
            print("-" * 80)

            # Correlations
            result = await db.execute(
                select(
                    func.count(CorrelationCalculation.id),
                    func.max(CorrelationCalculation.calculation_date)
                )
                .where(CorrelationCalculation.portfolio_id == portfolio.id)
            )
            corr_count, latest_corr = result.one()

            if corr_count > 0:
                print(f"✅ Correlations: {corr_count} records (latest: {latest_corr})")
            else:
                print(f"❌ Correlations: No calculations")

            # Portfolio Snapshots
            result = await db.execute(
                select(
                    func.count(PortfolioSnapshot.id),
                    func.max(PortfolioSnapshot.calculation_date)
                )
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            )
            snapshot_count, latest_snapshot = result.one()

            if snapshot_count > 0:
                print(f"✅ Portfolio Snapshots: {snapshot_count} records (latest: {latest_snapshot})")

                # Show latest snapshot details
                result = await db.execute(
                    select(PortfolioSnapshot)
                    .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                    .order_by(desc(PortfolioSnapshot.calculation_date))
                    .limit(1)
                )
                snapshot = result.scalar_one_or_none()

                if snapshot:
                    print(f"   Latest Snapshot Details:")
                    print(f"   - Total Value: ${snapshot.total_value:,.2f}")
                    print(f"   - Total Delta: {snapshot.total_delta:,.4f}")
                    print(f"   - Total Gamma: {snapshot.total_gamma:,.4f}")
                    print(f"   - Total Theta: {snapshot.total_theta:,.4f}")
                    print(f"   - Total Vega: {snapshot.total_vega:,.4f}")
            else:
                print(f"❌ Portfolio Snapshots: No calculations")

            print("")
            print("")

        # Global Summary
        print("=" * 80)
        print("GLOBAL SUMMARY")
        print("=" * 80)
        print("")

        # Total positions
        result = await db.execute(select(func.count(Position.id)))
        total_positions = result.scalar()
        print(f"Total Positions: {total_positions}")

        # Historical price coverage
        result = await db.execute(
            select(
                func.count(func.distinct(HistoricalPrice.symbol)),
                func.count(HistoricalPrice.id)
            )
        )
        unique_symbols, total_prices = result.one()
        print(f"Historical Prices: {total_prices} records across {unique_symbols} symbols")

        # Calculation totals
        result = await db.execute(select(func.count(PositionGreeks.id)))
        total_greeks = result.scalar()
        print(f"Position Greeks: {total_greeks} records")

        result = await db.execute(select(func.count(PositionFactorExposure.id)))
        total_factors = result.scalar()
        print(f"Factor Exposures: {total_factors} records")

        result = await db.execute(select(func.count(CorrelationCalculation.id)))
        total_corr = result.scalar()
        print(f"Correlations: {total_corr} records")

        result = await db.execute(select(func.count(PortfolioSnapshot.id)))
        total_snapshots = result.scalar()
        print(f"Portfolio Snapshots: {total_snapshots} records")

        print("")

        # Data completeness assessment
        print("-" * 80)
        print("DATA COMPLETENESS ASSESSMENT")
        print("-" * 80)

        # Positions with historical prices
        result = await db.execute(
            select(func.count(func.distinct(Position.id)))
            .select_from(Position)
            .join(HistoricalPrice, Position.symbol == HistoricalPrice.symbol)
        )
        positions_with_prices = result.scalar()
        coverage_pct = (positions_with_prices / total_positions * 100) if total_positions > 0 else 0

        status = "✅" if coverage_pct >= 80 else "⚠️" if coverage_pct >= 50 else "❌"
        print(f"{status} Historical Price Coverage: {positions_with_prices}/{total_positions} positions ({coverage_pct:.1f}%)")

        # Positions with factor exposures
        result = await db.execute(
            select(func.count(func.distinct(PositionFactorExposure.position_id)))
        )
        positions_with_factors = result.scalar()
        factor_pct = (positions_with_factors / total_positions * 100) if total_positions > 0 else 0

        status = "✅" if factor_pct >= 80 else "⚠️" if factor_pct >= 50 else "❌"
        print(f"{status} Factor Analysis Coverage: {positions_with_factors}/{total_positions} positions ({factor_pct:.1f}%)")

        # Options with Greeks
        result = await db.execute(
            select(func.count(Position.id))
            .where(Position.position_type.in_(['CALL', 'PUT']))
        )
        total_options = result.scalar()

        result = await db.execute(
            select(func.count(func.distinct(PositionGreeks.position_id)))
        )
        options_with_greeks = result.scalar()

        if total_options > 0:
            greeks_pct = (options_with_greeks / total_options * 100)
            status = "✅" if greeks_pct >= 80 else "⚠️" if greeks_pct >= 50 else "❌"
            print(f"{status} Options Greeks Coverage: {options_with_greeks}/{total_options} options ({greeks_pct:.1f}%)")
        else:
            print(f"ℹ️  No options positions in portfolio")

        # Portfolios with snapshots
        portfolios_with_snapshots = sum(1 for p in portfolios if True)  # Check below
        result = await db.execute(
            select(func.count(func.distinct(PortfolioSnapshot.portfolio_id)))
        )
        portfolios_with_snapshots = result.scalar()

        snapshot_pct = (portfolios_with_snapshots / len(portfolios) * 100) if len(portfolios) > 0 else 0
        status = "✅" if snapshot_pct >= 80 else "⚠️" if snapshot_pct >= 50 else "❌"
        print(f"{status} Portfolio Snapshots: {portfolios_with_snapshots}/{len(portfolios)} portfolios ({snapshot_pct:.1f}%)")

        print("")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(verify_database_state())
