#!/usr/bin/env python3
"""
Verify batch calculation results in Railway database

Checks if daily batch processing created expected calculation records:
- Position Greeks
- Factor Exposures
- Correlations
- Portfolio Snapshots

Usage:
  uv run python scripts/verification/verify_batch_results.py
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


async def verify_batch_results():
    """Verify batch calculation results."""
    print("=" * 70)
    print("BATCH CALCULATION RESULTS VERIFICATION")
    print("=" * 70)
    print("")

    async with get_async_session() as db:
        # 1. Portfolio counts
        result = await db.execute(select(func.count(Portfolio.id)))
        portfolio_count = result.scalar()
        print(f"📊 Portfolios: {portfolio_count}")

        result = await db.execute(select(func.count(Position.id)))
        position_count = result.scalar()
        print(f"📊 Positions: {position_count}")
        print("")

        # 2. Greeks calculations
        result = await db.execute(select(func.count(PositionGreeks.id)))
        greeks_count = result.scalar()

        result = await db.execute(
            select(func.max(PositionGreeks.calculation_date))
        )
        latest_greeks = result.scalar()

        status = "✅" if greeks_count > 0 else "❌"
        print(f"{status} Position Greeks: {greeks_count} records")
        if latest_greeks:
            print(f"   Latest calculation: {latest_greeks}")
        print("")

        # 3. Factor exposures
        result = await db.execute(select(func.count(PositionFactorExposure.id)))
        factor_count = result.scalar()

        result = await db.execute(
            select(func.max(PositionFactorExposure.calculation_date))
        )
        latest_factor = result.scalar()

        status = "✅" if factor_count > 0 else "❌"
        print(f"{status} Factor Exposures: {factor_count} records")
        if latest_factor:
            print(f"   Latest calculation: {latest_factor}")
        print("")

        # 4. Correlations
        result = await db.execute(select(func.count(CorrelationCalculation.id)))
        corr_count = result.scalar()

        result = await db.execute(
            select(func.max(CorrelationCalculation.calculation_date))
        )
        latest_corr = result.scalar()

        status = "✅" if corr_count > 0 else "❌"
        print(f"{status} Correlations: {corr_count} records")
        if latest_corr:
            print(f"   Latest calculation: {latest_corr}")
        print("")

        # 5. Portfolio snapshots
        result = await db.execute(select(func.count(PortfolioSnapshot.id)))
        snapshot_count = result.scalar()

        result = await db.execute(
            select(func.max(PortfolioSnapshot.calculation_date))
        )
        latest_snapshot = result.scalar()

        status = "✅" if snapshot_count > 0 else "❌"
        print(f"{status} Portfolio Snapshots: {snapshot_count} records")
        if latest_snapshot:
            print(f"   Latest snapshot: {latest_snapshot}")
        print("")

        # 6. Per-portfolio breakdown
        print("=" * 70)
        print("PER-PORTFOLIO BREAKDOWN")
        print("=" * 70)
        print("")

        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()

        for portfolio in portfolios:
            print(f"📁 {portfolio.name[:50]}")

            # Position count
            result = await db.execute(
                select(func.count(Position.id))
                .where(Position.portfolio_id == portfolio.id)
            )
            pos_count = result.scalar()
            print(f"   Positions: {pos_count}")

            # Greeks count for this portfolio's positions
            result = await db.execute(
                select(func.count(PositionGreeks.id))
                .join(Position, Position.id == PositionGreeks.position_id)
                .where(Position.portfolio_id == portfolio.id)
            )
            greeks = result.scalar()
            print(f"   Greeks: {greeks}")

            # Factor count for this portfolio's positions
            result = await db.execute(
                select(func.count(PositionFactorExposure.id))
                .join(Position, Position.id == PositionFactorExposure.position_id)
                .where(Position.portfolio_id == portfolio.id)
            )
            factors = result.scalar()
            print(f"   Factors: {factors}")

            # Snapshots for this portfolio
            result = await db.execute(
                select(func.count(PortfolioSnapshot.id))
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            )
            snapshots = result.scalar()
            print(f"   Snapshots: {snapshots}")
            print("")

        # 7. Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)

        has_greeks = greeks_count > 0
        has_factors = factor_count > 0
        has_correlations = corr_count > 0
        has_snapshots = snapshot_count > 0

        all_good = has_greeks and has_factors and has_correlations and has_snapshots

        if all_good:
            print("✅ All calculation engines produced results")
        else:
            print("⚠️  Some calculation engines missing results:")
            if not has_greeks:
                print("   ❌ Greeks calculations")
            if not has_factors:
                print("   ❌ Factor exposures")
            if not has_correlations:
                print("   ❌ Correlations")
            if not has_snapshots:
                print("   ❌ Portfolio snapshots")

        print("")


if __name__ == "__main__":
    asyncio.run(verify_batch_results())
