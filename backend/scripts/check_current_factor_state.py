"""
Check current state of factor data and beta calculations.

This script investigates:
1. Current factor values in FactorExposure table
2. Beta calculations in PortfolioSnapshot table
3. Position-level factor exposures
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, and_, desc
from uuid import UUID

from app.database import get_async_session
from app.models.users import Portfolio
from app.models.market_data import FactorExposure, FactorDefinition, PositionFactorExposure
from app.models.snapshots import PortfolioSnapshot


async def check_current_state():
    """Check current state of factor and beta data."""
    async with get_async_session() as db:
        print("=" * 80)
        print("CURRENT FACTOR & BETA STATE CHECK")
        print("=" * 80)
        print()

        # Get all portfolios
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = portfolios_result.scalars().all()

        today = date.today()
        yesterday = today - timedelta(days=1)

        for portfolio in portfolios:
            print(f"\n{'=' * 80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"ID: {portfolio.id}")
            print(f"{'=' * 80}")

            # 1. Check FactorExposure for recent dates
            print(f"\n1. PORTFOLIO-LEVEL FACTOR EXPOSURES (FactorExposure table)")
            print("-" * 80)

            for check_date in [today, yesterday]:
                print(f"\nDate: {check_date}")

                result = await db.execute(
                    select(FactorExposure, FactorDefinition)
                    .join(FactorDefinition)
                    .where(FactorExposure.portfolio_id == portfolio.id)
                    .where(FactorExposure.calculation_date == check_date)
                    .order_by(FactorDefinition.name)
                )

                exposures = result.all()
                if exposures:
                    for fe, fd in exposures:
                        print(f"  {fd.name:20s}: {fe.exposure_value:12.6f} (${fe.exposure_dollar:12.2f})")
                else:
                    print(f"  No factor exposures found")

            # 2. Check PortfolioSnapshot for beta calculations
            print(f"\n\n2. PORTFOLIO SNAPSHOTS (Beta Calculations)")
            print("-" * 80)

            for check_date in [today, yesterday]:
                print(f"\nDate: {check_date}")

                snapshot_result = await db.execute(
                    select(PortfolioSnapshot)
                    .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                    .where(PortfolioSnapshot.snapshot_date == check_date)
                )

                snapshot = snapshot_result.scalar_one_or_none()
                if snapshot:
                    print(f"  Beta (Calculated 90d): {snapshot.beta_calculated_90d}")
                    print(f"  Beta (Provider 1y):    {snapshot.beta_provider_1y}")
                    print(f"  Snapshot exists:       Yes")
                else:
                    print(f"  No snapshot found")

            # 3. Check PositionFactorExposure for position-level data
            print(f"\n\n3. POSITION-LEVEL FACTOR EXPOSURES (PositionFactorExposure table)")
            print("-" * 80)

            for check_date in [today, yesterday]:
                print(f"\nDate: {check_date}")

                # Get count by factor type
                pos_result = await db.execute(
                    select(
                        FactorDefinition.name,
                        FactorDefinition.factor_type,
                        FactorDefinition.calculation_method
                    )
                    .join(PositionFactorExposure)
                    .where(PositionFactorExposure.calculation_date == check_date)
                    .distinct()
                )

                factors_found = pos_result.all()
                if factors_found:
                    # Group by type
                    by_type = {}
                    for name, ftype, method in factors_found:
                        key = f"{ftype} ({method})"
                        if key not in by_type:
                            by_type[key] = []
                        by_type[key].append(name)

                    for key, names in by_type.items():
                        print(f"  {key}:")
                        for name in sorted(names):
                            print(f"    - {name}")
                else:
                    print(f"  No position-level exposures found")

            # 4. Check most recent data available
            print(f"\n\n4. MOST RECENT DATA AVAILABLE")
            print("-" * 80)

            # Most recent FactorExposure
            recent_fe_result = await db.execute(
                select(FactorExposure.calculation_date)
                .where(FactorExposure.portfolio_id == portfolio.id)
                .order_by(desc(FactorExposure.calculation_date))
                .limit(1)
            )
            recent_fe_date = recent_fe_result.scalar_one_or_none()
            print(f"  Most recent FactorExposure:         {recent_fe_date}")

            # Most recent PortfolioSnapshot
            recent_snap_result = await db.execute(
                select(PortfolioSnapshot.snapshot_date)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(desc(PortfolioSnapshot.snapshot_date))
                .limit(1)
            )
            recent_snap_date = recent_snap_result.scalar_one_or_none()
            print(f"  Most recent PortfolioSnapshot:      {recent_snap_date}")

            # Most recent PositionFactorExposure
            recent_pfe_result = await db.execute(
                select(PositionFactorExposure.calculation_date)
                .order_by(desc(PositionFactorExposure.calculation_date))
                .limit(1)
            )
            recent_pfe_date = recent_pfe_result.scalar_one_or_none()
            print(f"  Most recent PositionFactorExposure: {recent_pfe_date}")

        print(f"\n{'=' * 80}")
        print("CHECK COMPLETE")
        print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(check_current_state())
