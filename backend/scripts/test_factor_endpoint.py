"""
Quick test to verify factor exposure endpoint works with new staleness metadata
"""
import asyncio
from uuid import UUID
from app.database import get_async_session
from app.services.factor_exposure_service import FactorExposureService


async def test_endpoint():
    # Use Demo Individual portfolio
    demo_individual_id = UUID('c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e')

    async with get_async_session() as db:
        svc = FactorExposureService(db)
        result = await svc.get_portfolio_exposures(demo_individual_id)

        print('=' * 80)
        print('FACTOR EXPOSURE ENDPOINT TEST')
        print('=' * 80)
        print(f'Available: {result.get("available")}')
        print(f'Portfolio ID: {result.get("portfolio_id")}')
        print(f'Calculation Date: {result.get("calculation_date")}')
        print()

        # Check data_quality structure
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
            print('First 3 Factors:')
            for factor in result.get('factors', [])[:3]:
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
            print('✅ Response validates against schema')
        except Exception as e:
            print(f'❌ Schema validation failed: {e}')

        print('=' * 80)


if __name__ == "__main__":
    asyncio.run(test_endpoint())
