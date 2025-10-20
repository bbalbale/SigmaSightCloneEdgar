"""
Test Claude Sonnet 4 investigation with fresh data.
"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.ai_insights import InsightType
from app.services.analytical_reasoning_service import analytical_reasoning_service


async def test_claude():
    """Test Claude Sonnet 4 investigation."""
    print("\n=== Testing Claude Sonnet 4 Investigation ===\n")

    async with get_async_session() as db:
        # Get first demo portfolio
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("ERROR: No portfolios found in database")
            return

        print(f"Testing with portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}\n")

        # Run fresh investigation with different focus to avoid cache
        print("Running Claude investigation (focus: hedge_effectiveness)...")
        insight = await analytical_reasoning_service.investigate_portfolio(
            db=db,
            portfolio_id=portfolio.id,
            insight_type=InsightType.DAILY_SUMMARY,
            focus_area="hedge_effectiveness",  # Different from previous test
        )

        print(f"\n=== Claude Investigation Complete ===\n")
        print(f"Insight ID: {insight.id}")
        print(f"Type: {insight.insight_type}")
        print(f"Title: {insight.title}")
        print(f"Severity: {insight.severity}")
        print(f"\nSummary:")
        print(f"{insight.summary}\n")
        print(f"Key Findings ({len(insight.key_findings or [])}):")
        for i, finding in enumerate((insight.key_findings or [])[:5], 1):
            print(f"  {i}. {finding}")
        print(f"\nRecommendations ({len(insight.recommendations or [])}):")
        for i, rec in enumerate((insight.recommendations or [])[:5], 1):
            print(f"  {i}. {rec}")
        print(f"\nData Limitations:")
        print(f"{insight.data_limitations}\n")
        print(f"Performance Metrics:")
        print(f"  Cost: ${insight.cost_usd:.4f}")
        print(f"  Time: {insight.generation_time_ms:.0f}ms")
        print(f"  Tokens In: {insight.token_count_input}")
        print(f"  Tokens Out: {insight.token_count_output}")
        print(f"  Model: {insight.model_used}")
        print(f"  Provider: {insight.provider}")

        print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    asyncio.run(test_claude())
