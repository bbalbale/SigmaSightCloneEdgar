"""
Compare HNW vs Demo Individual portfolio factor exposures.
"""
import asyncio
import json
from uuid import UUID
from app.database import get_async_session
from app.services.factor_exposure_service import FactorExposureService


async def compare_portfolios():
    """Compare HNW vs Demo Individual factor exposures"""
    hnw_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    demo_id = UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe')

    print("=" * 80)
    print("COMPARING HNW VS DEMO INDIVIDUAL FACTOR EXPOSURES")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        svc = FactorExposureService(db)

        # Get HNW factors
        print("1. HNW Portfolio (what user is viewing):")
        print("-" * 80)
        hnw_result = await svc.get_portfolio_exposures(hnw_id)

        print(f"Available: {hnw_result.get('available')}")
        print(f"Calculation Date: {hnw_result.get('calculation_date')}")
        print(f"Number of Factors: {len(hnw_result.get('factors', []))}")
        print()

        if hnw_result.get('factors'):
            print("Factors:")
            for factor in hnw_result['factors']:
                print(f"  {factor['name']:35s} beta={factor['beta']:10.6f}  dollar=${factor.get('exposure_dollar', 'N/A')}")
        else:
            print("❌ NO FACTORS RETURNED FOR HNW!")
        print()

        # Get Demo Individual factors
        print("2. Demo Individual Portfolio (tested and working):")
        print("-" * 80)
        demo_result = await svc.get_portfolio_exposures(demo_id)

        print(f"Available: {demo_result.get('available')}")
        print(f"Calculation Date: {demo_result.get('calculation_date')}")
        print(f"Number of Factors: {len(demo_result.get('factors', []))}")
        print()

        if demo_result.get('factors'):
            print("Factors:")
            for factor in demo_result['factors']:
                print(f"  {factor['name']:35s} beta={factor['beta']:10.6f}  dollar=${factor.get('exposure_dollar', 'N/A')}")
        print()

        # Comparison
        print("3. COMPARISON:")
        print("-" * 80)
        hnw_count = len(hnw_result.get('factors', []))
        demo_count = len(demo_result.get('factors', []))

        print(f"HNW Factor Count:  {hnw_count}")
        print(f"Demo Factor Count: {demo_count}")
        print()

        if hnw_count == 0 and demo_count > 0:
            print("⚠️ ISSUE: HNW portfolio has NO factors but Demo Individual has {demo_count} factors")
            print("This explains why user sees zeros on the dashboard!")
            print()
            print("Possible causes:")
            print("1. HNW portfolio doesn't have ridge factor calculations for today")
            print("2. HNW portfolio is missing factor exposures in the database")
            print("3. Different calculation dates between portfolios")
        elif hnw_count > 0 and hnw_count < demo_count:
            print(f"⚠️ HNW portfolio has FEWER factors ({hnw_count}) than Demo ({demo_count})")
            print("Missing factors:")
            hnw_names = set(f['name'] for f in hnw_result.get('factors', []))
            demo_names = set(f['name'] for f in demo_result.get('factors', []))
            for missing in demo_names - hnw_names:
                print(f"  - {missing}")
        elif hnw_count == demo_count and hnw_count > 0:
            print("✅ Both portfolios have the same number of factors")
            print("Issue may be in frontend display or API response parsing")

        # Show full JSON for debugging
        print()
        print("4. FULL SERVICE RESPONSES (JSON):")
        print("-" * 80)
        print("\nHNW Result:")
        print(json.dumps(hnw_result, indent=2, default=str))
        print("\nDemo Individual Result:")
        print(json.dumps(demo_result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(compare_portfolios())
