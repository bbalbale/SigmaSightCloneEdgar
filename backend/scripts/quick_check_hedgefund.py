import asyncio
from uuid import UUID
from app.database import get_async_session
from app.services.factor_exposure_service import FactorExposureService

async def quick_check():
    hedgefund_id = UUID('fcd71196-e93e-f000-5a74-31a9eead3118')
    async with get_async_session() as db:
        svc = FactorExposureService(db)
        result = await svc.get_portfolio_exposures(hedgefund_id)

        print('=' * 80)
        print('HEDGE FUND PORTFOLIO FACTOR EXPOSURES (AFTER RECALCULATION)')
        print('=' * 80)
        print(f'Available: {result.get("available")}')
        print(f'Number of Factors: {len(result.get("factors", []))}')
        print()

        if result.get('factors'):
            print('Factors:')
            for factor in result.get('factors', []):
                print(f'  {factor["name"]:35s} beta={factor["beta"]:10.6f}')
        else:
            print('❌ NO FACTORS!')

        print()
        print('Expected: 8 factors with large beta values')
        print('=' * 80)

asyncio.run(quick_check())
