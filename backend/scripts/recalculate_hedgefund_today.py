"""
Recalculate Hedge Fund portfolio for today (Oct 22, 2025) with correct ridge scaling.
This will fix both the ridge factor values and calculate the missing market betas.
"""
import asyncio
from datetime import date
from uuid import UUID
from app.database import get_async_session
from app.calculations.factors_ridge import calculate_factor_betas_ridge
from app.calculations.market_beta import calculate_portfolio_market_beta, calculate_portfolio_provider_beta
from app.calculations.snapshots import create_portfolio_snapshot
from app.services.factor_exposure_service import FactorExposureService


async def recalculate_hedgefund():
    """Recalculate Hedge Fund portfolio for today"""
    hedgefund_id = UUID('fcd71196-e93e-f000-5a74-31a9eead3118')
    today = date(2025, 10, 22)

    print("=" * 80)
    print("RECALCULATING HEDGE FUND PORTFOLIO FOR OCT 22, 2025")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # 1. Recalculate ridge factors with correct scaling
        print("1. Recalculating ridge regression factors...")
        print("-" * 80)
        ridge_result = await calculate_factor_betas_ridge(
            db=db,
            portfolio_id=hedgefund_id,
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
            portfolio_id=hedgefund_id,
            calculation_date=today,
            window_days=90
        )

        # Calculate 1-year provider beta
        beta_1y_result = await calculate_portfolio_provider_beta(
            db=db,
            portfolio_id=hedgefund_id,
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

        # 3. Create/update portfolio snapshot
        print("3. Creating/updating portfolio snapshot...")
        print("-" * 80)
        snapshot_result = await create_portfolio_snapshot(db, hedgefund_id, today)

        if snapshot_result.get('success'):
            print(f"✅ Snapshot updated successfully")
        else:
            print(f"❌ Snapshot update failed: {snapshot_result.get('error')}")
        print()

        # 4. Verify the results
        print("4. Verifying results...")
        print("-" * 80)

        # Check factor exposures
        svc = FactorExposureService(db)
        exposures = await svc.get_portfolio_exposures(hedgefund_id)

        print(f"Factors now available: {len(exposures.get('factors', []))}")
        if exposures.get('factors'):
            print("\nFactor values:")
            for factor in exposures['factors']:
                print(f"  {factor['name']:35s} beta={factor['beta']:10.6f}")
        else:
            print("❌ NO FACTORS!")
        print()

        print("=" * 80)
        print("RECALCULATION COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(recalculate_hedgefund())
