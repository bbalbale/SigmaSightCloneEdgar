"""
Debug the factor exposure service to see exactly what it's returning.
"""
import asyncio
import json
from uuid import UUID
from app.database import get_async_session
from app.services.factor_exposure_service import FactorExposureService


async def debug_service():
    """Debug what the factor service is actually returning"""
    portfolio_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')  # Demo Individual

    print(f"=" * 80)
    print(f"DEBUGGING FACTOR EXPOSURE SERVICE")
    print(f"Portfolio ID: {portfolio_id}")
    print(f"=" * 80)
    print()

    async with get_async_session() as db:
        svc = FactorExposureService(db)
        result = await svc.get_portfolio_exposures(portfolio_id)

    print("SERVICE RESULT:")
    print("-" * 80)
    print(json.dumps(result, indent=2, default=str))
    print()

    print("ANALYSIS:")
    print("-" * 80)
    print(f"Available: {result.get('available')}")
    print(f"Calculation Date: {result.get('calculation_date')}")
    print(f"Number of Factors: {len(result.get('factors', []))}")
    print()

    if result.get('factors'):
        print("FACTOR DETAILS:")
        for factor in result['factors']:
            print(f"  {factor['name']:35s} beta={factor['beta']:10.6f}  dollar=${factor.get('exposure_dollar', 'N/A')}")
    else:
        print("⚠️ NO FACTORS RETURNED!")

    if result.get('data_quality'):
        print(f"\nData Quality Info:")
        print(f"  {result['data_quality']}")

    if result.get('metadata'):
        print(f"\nMetadata:")
        for key, value in result['metadata'].items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(debug_service())
