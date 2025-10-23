"""
Recalculate HNW portfolio for today (Oct 22, 2025) with correct ridge scaling.
This will fix both the ridge factor values and calculate the missing market betas.
"""
import asyncio
from datetime import date
from uuid import UUID
from app.database import get_async_session
from app.calculations.factors_ridge import calculate_factor_betas_ridge
from app.calculations.market_beta import calculate_portfolio_market_beta, calculate_portfolio_provider_beta
from app.services.factor_exposure_service import FactorExposureService
from sqlalchemy import select
from app.models.snapshots import PortfolioSnapshot


async def recalculate_hnw():
    """Recalculate HNW portfolio for today"""
    hnw_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    today = date(2025, 10, 22)

    print("=" * 80)
    print("RECALCULATING HNW PORTFOLIO FOR OCT 22, 2025")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # 1. Recalculate ridge factors with correct scaling
        print("1. Recalculating ridge regression factors...")
        print("-" * 80)
        ridge_result = await calculate_factor_betas_ridge(
            db=db,
            portfolio_id=hnw_id,
            calculation_date=today,
            regularization_alpha=1.0,
            use_delta_adjusted=False,
            context=None
        )

        if ridge_result.get('success'):
            print(f"✅ Ridge calculation successful")
            print(f"   Factors calculated: {ridge_result.get('factors_calculated', 0)}")
        else:
            print(f"❌ Ridge calculation failed: {ridge_result.get('error')}")
        print()

        # 2. Recalculate portfolio betas
        print("2. Recalculating portfolio market betas...")
        print("-" * 80)

        # Calculate 90-day calculated beta
        beta_90d_result = await calculate_portfolio_market_beta(
            db=db,
            portfolio_id=hnw_id,
            calculation_date=today,
            window_days=90
        )

        # Calculate 1-year provider beta
        beta_1y_result = await calculate_portfolio_provider_beta(
            db=db,
            portfolio_id=hnw_id,
            calculation_date=today
        )

        if beta_90d_result.get('success'):
            print(f"✅ Beta 90d calculation successful")
            print(f"   Beta 90d: {beta_90d_result.get('beta')}")
        else:
            print(f"❌ Beta 90d calculation failed: {beta_90d_result.get('error')}")

        if beta_1y_result.get('success'):
            print(f"✅ Beta 1y calculation successful")
            print(f"   Beta 1y: {beta_1y_result.get('beta')}")
        else:
            print(f"❌ Beta 1y calculation failed: {beta_1y_result.get('error')}")
        print()

        # 3. Verify the results
        print("3. Verifying results...")
        print("-" * 80)

        # Check factor exposures
        svc = FactorExposureService(db)
        exposures = await svc.get_portfolio_exposures(hnw_id)

        print(f"Factors now available: {len(exposures.get('factors', []))}")
        if exposures.get('factors'):
            print("\nFactor values:")
            for factor in exposures['factors']:
                print(f"  {factor['name']:35s} beta={factor['beta']:10.6f}")
        print()

        # Check snapshot betas
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == hnw_id)
            .where(PortfolioSnapshot.snapshot_date == today)
        )
        snapshot = result.scalar_one_or_none()

        if snapshot:
            print("Snapshot betas:")
            print(f"  Beta Calculated 90d: {snapshot.beta_calculated_90d}")
            print(f"  Beta Provider 1y: {snapshot.beta_provider_1y}")
        else:
            print("❌ No snapshot found for today")
        print()

        print("=" * 80)
        print("RECALCULATION COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(recalculate_hnw())
