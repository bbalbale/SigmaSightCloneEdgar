"""
Test factor exposure endpoint with HNW portfolio (has data from Oct 22)
"""
import asyncio
from uuid import UUID
from app.database import get_async_session
from app.services.factor_exposure_service import FactorExposureService


async def test_endpoint():
    # Use HNW portfolio (recalculated for Oct 22)
    hnw_id = UUID('3d6c9e5c-1a8f-48b7-9b3e-7f4e5c6d7e8f')

    async with get_async_session() as db:
        svc = FactorExposureService(db)
        result = await svc.get_portfolio_exposures(hnw_id)

        print('=' * 80)
        print('HNW PORTFOLIO FACTOR EXPOSURE TEST (WITH STALENESS METADATA)')
        print('=' * 80)
        print(f'Available: {result.get("available")}')
        print(f'Portfolio ID: {result.get("portfolio_id")}')
        print(f'Calculation Date: {result.get("calculation_date")}')
        print()

        # Check data_quality structure (should be DataStalenessInfo for available=True)
        data_quality = result.get('data_quality')
        if data_quality:
            print('Data Quality Metadata:')
            if isinstance(data_quality, dict):
                for key, value in data_quality.items():
                    print(f'  {key}: {value}')
            else:
                print(f'  Type: {type(data_quality)}')
                print(f'  Value: {data_quality}')
        else:
            print('❌ No data_quality field!')

        print()
        print(f'Number of Factors: {len(result.get("factors", []))}')

        if result.get('factors'):
            print()
            print('All Factors:')
            for factor in result.get('factors', []):
                print(f'  {factor["name"]:35s} beta={factor["beta"]:10.6f}')

        print()
        print('Metadata:')
        metadata = result.get('metadata', {})
        for key, value in metadata.items():
            print(f'  {key}: {value}')

        print('=' * 80)

        # Check if this would be valid against the Pydantic schema
        from app.schemas.analytics import PortfolioFactorExposuresResponse
        try:
            response = PortfolioFactorExposuresResponse(**result)
            print('✅ Response validates against PortfolioFactorExposuresResponse schema')
        except Exception as e:
            print(f'❌ Schema validation failed: {e}')

        print('=' * 80)


if __name__ == "__main__":
    asyncio.run(test_endpoint())
