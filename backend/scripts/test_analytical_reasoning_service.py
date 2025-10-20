"""
Test the AnalyticalReasoningService basic functionality.
"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.ai_insights import InsightType
from app.services.analytical_reasoning_service import analytical_reasoning_service


async def test_service():
    """Test basic service functionality."""
    print("\n=== Testing AnalyticalReasoningService ===\n")

    async with get_async_session() as db:
        # Get first demo portfolio
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("ERROR: No portfolios found in database")
            return

        print(f"Testing with portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}\n")

        # Test investigation
        print("Running investigation...")
        insight = await analytical_reasoning_service.investigate_portfolio(
            db=db,
            portfolio_id=portfolio.id,
            insight_type=InsightType.DAILY_SUMMARY,
            focus_area="volatility",
        )

        print(f"\nOK - Investigation complete!")
        print(f"  Insight ID: {insight.id}")
        print(f"  Type: {insight.insight_type.value}")
        print(f"  Title: {insight.title}")
        print(f"  Severity: {insight.severity.value}")
        print(f"  Summary: {insight.summary}")
        print(f"  Key Findings: {len(insight.key_findings or [])} findings")
        print(f"  Recommendations: {len(insight.recommendations or [])} recommendations")
        print(f"  Cache Key: {insight.cache_key[:16]}...")
        print(f"  Created: {insight.created_at}")

        # Test cache hit
        print("\n\nTesting cache lookup (should hit cache)...")
        cached_insight = await analytical_reasoning_service.investigate_portfolio(
            db=db,
            portfolio_id=portfolio.id,
            insight_type=InsightType.DAILY_SUMMARY,
            focus_area="volatility",
        )

        if cached_insight.id == insight.id:
            print("OK - Cache hit! Returned same insight")
        else:
            print("WARNING: Did not hit cache")

        print(f"  Cache Hit Flag: {cached_insight.cache_hit}")

        print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    asyncio.run(test_service())
