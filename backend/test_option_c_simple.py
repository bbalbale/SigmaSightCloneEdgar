"""
Simple Option C Test (no unicode)
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.services.analytics_bundle import analytics_bundle_service
from app.services.analytical_reasoning_service import analytical_reasoning_service
from app.models.ai_insights import InsightType


async def test_analytics_bundle():
    """Test analytics bundle fetching"""
    print("\n" + "="*60)
    print("TEST 1: Analytics Bundle Fetching")
    print("="*60)

    async with AsyncSessionLocal() as db:
        try:
            # Get first portfolio
            result = await db.execute(select(Portfolio).limit(1))
            portfolio = result.scalar_one_or_none()

            if not portfolio:
                print("ERROR: No portfolios found in database")
                print("Run: python scripts/database/reset_and_seed.py seed")
                return None

            print(f"\nFound test portfolio: {portfolio.account_name}")
            print(f"  ID: {portfolio.id}")

            # Test analytics bundle fetch
            print("\nFetching analytics bundle...")
            bundle = await analytics_bundle_service.fetch_portfolio_analytics_bundle(
                db=db,
                portfolio_id=portfolio.id,
                focus_area=None
            )

            print(f"\nAnalytics bundle fetched successfully!")
            print(f"  Metrics available:")
            for key, value in bundle.items():
                if key != "focus_area":
                    status = "YES" if value is not None else "NO"
                    print(f"    {status} - {key}")

            return portfolio.id

        except Exception as e:
            print(f"ERROR fetching analytics bundle: {e}")
            import traceback
            traceback.print_exc()
            return None


async def test_context_merging(portfolio_id):
    """Test that context is merged correctly"""
    print("\n" + "="*60)
    print("TEST 2: Context Merging")
    print("="*60)

    async with AsyncSessionLocal() as db:
        try:
            # Call the context builder directly
            context = await analytical_reasoning_service._build_investigation_context(
                db=db,
                portfolio_id=portfolio_id,
                focus_area=None
            )

            print(f"\nContext merged successfully!")
            print(f"  Keys in context: {len(context)}")
            print(f"  Analytics bundle available: {context.get('analytics_bundle_available', False)}")

            if "pre_calculated_analytics" in context:
                analytics = context["pre_calculated_analytics"]
                available = len([k for k, v in analytics.items() if v is not None])
                print(f"  Pre-calculated metrics: {available}/7")

            return True

        except Exception as e:
            print(f"ERROR merging context: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_full_insight_generation(portfolio_id):
    """Test full insight generation with Option C"""
    print("\n" + "="*60)
    print("TEST 3: Full Insight Generation (Option C)")
    print("="*60)
    print("\nThis will call Claude API - make sure ANTHROPIC_API_KEY is set!")
    print("Expected: ~18-22s, ~$0.02, tool_calls_count = 0")

    response = input("\nProceed with API call? (y/n): ")
    if response.lower() != 'y':
        print("Skipped.")
        return

    async with AsyncSessionLocal() as db:
        try:
            print("\nGenerating insight...")
            insight = await analytical_reasoning_service.investigate_portfolio(
                db=db,
                portfolio_id=portfolio_id,
                insight_type=InsightType.DAILY_SUMMARY,
                focus_area=None,
                user_question=None,
                auth_token=None
            )

            print(f"\nInsight generated successfully!")
            print(f"\n  Title: {insight.title}")
            print(f"  Severity: {insight.severity}")
            print(f"  Summary: {insight.summary[:100]}...")
            print(f"\n  Performance Metrics:")
            print(f"    Generation time: {insight.generation_time_ms/1000:.1f}s")
            print(f"    Cost: ${insight.cost_usd:.4f}")
            print(f"    Tool calls: {insight.tool_calls_count}")
            print(f"    Token count: {insight.token_count_input + insight.token_count_output}")

            # Check if it meets Option C expectations
            print(f"\n  Option C Validation:")
            check1 = "PASS" if insight.tool_calls_count == 0 else "WARN"
            check2 = "PASS" if 15000 <= insight.generation_time_ms <= 25000 else "WARN"
            check3 = "PASS" if insight.cost_usd <= 0.03 else "WARN"

            print(f"    {check1} - Tool calls = 0: {insight.tool_calls_count == 0}")
            print(f"    {check2} - Time 15-25s: {15000 <= insight.generation_time_ms <= 25000}")
            print(f"    {check3} - Cost <= $0.03: {insight.cost_usd <= 0.03}")

        except Exception as e:
            print(f"ERROR generating insight: {e}")
            import traceback
            traceback.print_exc()


async def main():
    print("\n" + "="*60)
    print("OPTION C: Hybrid Interpretation-First - Test Suite")
    print("="*60)

    # Test 1: Analytics bundle fetching
    portfolio_id = await test_analytics_bundle()

    if not portfolio_id:
        print("\nERROR: Cannot continue - no portfolio found")
        return

    # Test 2: Context merging
    success = await test_context_merging(portfolio_id)

    if not success:
        print("\nERROR: Cannot continue - context merging failed")
        return

    # Test 3: Full insight generation (optional - requires API key)
    await test_full_insight_generation(portfolio_id)

    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
