"""
Test Option C: Hybrid Interpretation-First Implementation

This script tests that:
1. Analytics bundle is fetched successfully
2. Context is merged correctly
3. Claude receives interpretation-first prompts
4. Tool usage is tracked
"""
import asyncio
from uuid import UUID
from app.database import AsyncSessionLocal
from app.services.analytics_bundle import analytics_bundle_service
from app.services.analytical_reasoning_service import analytical_reasoning_service
from app.models.ai_insights import InsightType


async def test_analytics_bundle():
    """Test analytics bundle fetching"""
    print("\n" + "="*60)
    print("TEST 1: Analytics Bundle Fetching")
    print("="*60)

    # Use demo portfolio ID (you'll need to get this from your database)
    # For now, let's just test the import works
    print("✓ analytics_bundle_service imported successfully")
    print(f"  Type: {type(analytics_bundle_service).__name__}")

    # Test with actual portfolio ID
    async with AsyncSessionLocal() as db:
        try:
            # Get a demo portfolio ID first
            from sqlalchemy import select
            from app.models.users import Portfolio

            result = await db.execute(
                select(Portfolio)
                .limit(1)
            )
            portfolio = result.scalar_one_or_none()

            if not portfolio:
                print("❌ No portfolios found in database")
                print("   Run: python scripts/database/reset_and_seed.py seed")
                return None

            print(f"\n✓ Found test portfolio: {portfolio.account_name}")
            print(f"  ID: {portfolio.id}")

            # Test analytics bundle fetch
            print("\n  Fetching analytics bundle...")
            bundle = await analytics_bundle_service.fetch_portfolio_analytics_bundle(
                db=db,
                portfolio_id=portfolio.id,
                focus_area=None
            )

            print(f"\n✓ Analytics bundle fetched successfully!")
            print(f"  Metrics available:")
            for key, value in bundle.items():
                if key != "focus_area":
                    status = "✓" if value is not None else "✗"
                    print(f"    {status} {key}: {'Available' if value else 'Missing'}")

            return portfolio.id

        except Exception as e:
            print(f"❌ Error fetching analytics bundle: {e}")
            import traceback
            traceback.print_exc()
            return None


async def test_context_merging(portfolio_id: UUID):
    """Test that context is merged correctly"""
    print("\n" + "="*60)
    print("TEST 2: Context Merging")
    print("="*60)

    async with AsyncSessionLocal() as db:
        try:
            # Call the context builder directly
            from app.services.analytical_reasoning_service import analytical_reasoning_service

            context = await analytical_reasoning_service._build_investigation_context(
                db=db,
                portfolio_id=portfolio_id,
                focus_area=None
            )

            print(f"\n✓ Context merged successfully!")
            print(f"  Keys in context: {len(context)}")
            print(f"  Analytics bundle available: {context.get('analytics_bundle_available', False)}")

            if "pre_calculated_analytics" in context:
                analytics = context["pre_calculated_analytics"]
                print(f"  Pre-calculated metrics: {len([k for k, v in analytics.items() if v is not None])}/7")

            return True

        except Exception as e:
            print(f"❌ Error merging context: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_full_insight_generation(portfolio_id: UUID):
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

            print(f"\n✓ Insight generated successfully!")
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
            print(f"    {'✓' if insight.tool_calls_count == 0 else '⚠'} Tool calls = 0 (interpreted): {insight.tool_calls_count == 0}")
            print(f"    {'✓' if 15000 <= insight.generation_time_ms <= 25000 else '⚠'} Time 15-25s: {15000 <= insight.generation_time_ms <= 25000}")
            print(f"    {'✓' if insight.cost_usd <= 0.03 else '⚠'} Cost <= $0.03: {insight.cost_usd <= 0.03}")

        except Exception as e:
            print(f"❌ Error generating insight: {e}")
            import traceback
            traceback.print_exc()


async def main():
    print("\n" + "="*60)
    print("OPTION C: Hybrid Interpretation-First - Test Suite")
    print("="*60)

    # Test 1: Analytics bundle fetching
    portfolio_id = await test_analytics_bundle()

    if not portfolio_id:
        print("\n❌ Cannot continue - no portfolio found")
        return

    # Test 2: Context merging
    success = await test_context_merging(portfolio_id)

    if not success:
        print("\n❌ Cannot continue - context merging failed")
        return

    # Test 3: Full insight generation (optional - requires API key)
    await test_full_insight_generation(portfolio_id)

    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
