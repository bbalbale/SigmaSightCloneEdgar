"""
Debug the HNW portfolio factor exposures specifically.
User is viewing this portfolio and seeing zeros.
"""
import asyncio
import json
from uuid import UUID
from datetime import date
from app.database import get_async_session
from app.services.factor_exposure_service import FactorExposureService
from sqlalchemy import select, desc
from app.models.market_data import FactorExposure, PositionFactorExposure
from app.models.snapshots import PortfolioSnapshot


async def debug_hnw_portfolio():
    """Debug HNW portfolio factor exposures"""
    hnw_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    demo_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')

    print("=" * 80)
    print("DEBUGGING HNW PORTFOLIO FACTOR EXPOSURES")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # Check FactorExposure table for HNW
        print("1. FactorExposure table (portfolio-level aggregated betas):")
        print("-" * 80)
        result = await db.execute(
            select(FactorExposure)
            .where(FactorExposure.portfolio_id == hnw_id)
            .order_by(desc(FactorExposure.calculation_date))
            .limit(5)
        )
        hnw_factors = result.scalars().all()

        if hnw_factors:
            print(f"✅ Found {len(hnw_factors)} factor exposure records for HNW")
            latest = hnw_factors[0]
            print(f"Latest date: {latest.calculation_date}")
            print(f"Factor: {latest.factor_name}")
            print(f"Beta: {latest.beta}")
            print(f"Dollar exposure: ${latest.exposure_dollar:,.2f}")
            print()
            print("All recent factors:")
            for f in hnw_factors:
                print(f"  {f.calculation_date} | {f.factor_name:20s} | beta={f.beta:10.6f} | ${f.exposure_dollar:,.2f}")
        else:
            print("❌ NO factor exposures found for HNW portfolio!")
        print()

        # Check PortfolioSnapshot for market betas
        print("2. PortfolioSnapshot (market betas):")
        print("-" * 80)
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == hnw_id)
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .limit(3)
        )
        hnw_snapshots = result.scalars().all()

        if hnw_snapshots:
            print(f"✅ Found {len(hnw_snapshots)} snapshots for HNW")
            for snap in hnw_snapshots:
                print(f"  {snap.snapshot_date} | Beta 90d: {snap.beta_calculated_90d} | Beta 1y: {snap.beta_provider_1y}")
        else:
            print("❌ NO snapshots found for HNW portfolio!")
        print()

        # Test the factor exposure service
        print("3. Factor Exposure Service Response:")
        print("-" * 80)
        svc = FactorExposureService(db)
        hnw_result = await svc.get_portfolio_exposures(hnw_id)

        print(f"Available: {hnw_result.get('available')}")
        print(f"Calculation Date: {hnw_result.get('calculation_date')}")
        print(f"Number of Factors: {len(hnw_result.get('factors', []))}")
        print()

        if hnw_result.get('factors'):
            print("Factors returned by service:")
            for factor in hnw_result['factors']:
                print(f"  {factor['name']:35s} beta={factor['beta']:10.6f}  dollar=${factor.get('exposure_dollar', 'N/A')}")
        else:
            print("❌ NO FACTORS RETURNED BY SERVICE!")
        print()

        # Compare with Demo Individual
        print("4. COMPARISON: Demo Individual vs HNW")
        print("-" * 80)
        demo_result = await svc.get_portfolio_exposures(demo_id)

        print(f"Demo Individual: {len(demo_result.get('factors', []))} factors, available={demo_result.get('available')}")
        print(f"HNW:             {len(hnw_result.get('factors', []))} factors, available={hnw_result.get('available')}")
        print()

        if demo_result.get('factors') and not hnw_result.get('factors'):
            print("⚠️ ISSUE: Demo Individual has factors but HNW doesn't!")
            print()
            print("Demo factors:")
            for f in demo_result['factors']:
                print(f"  {f['name']:35s} beta={f['beta']:10.6f}")

        # Check position-level factor exposures for HNW
        print()
        print("5. PositionFactorExposure (position-level betas):")
        print("-" * 80)
        result = await db.execute(
            select(PositionFactorExposure)
            .where(PositionFactorExposure.portfolio_id == hnw_id)
            .order_by(desc(PositionFactorExposure.calculation_date))
            .limit(10)
        )
        hnw_position_factors = result.scalars().all()

        if hnw_position_factors:
            print(f"✅ Found {len(hnw_position_factors)} position-level factor exposures for HNW")
            for pf in hnw_position_factors[:5]:
                print(f"  {pf.calculation_date} | Position: {pf.position_id} | Factor: {pf.factor_name} | beta={pf.beta:10.6f}")
        else:
            print("❌ NO position-level factor exposures found for HNW portfolio!")


if __name__ == "__main__":
    asyncio.run(debug_hnw_portfolio())
