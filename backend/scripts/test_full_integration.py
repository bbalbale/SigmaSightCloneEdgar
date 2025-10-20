"""
Test full AI Analytical Reasoning integration with real data.
"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.ai_insights import InsightType
from app.services.analytical_reasoning_service import analytical_reasoning_service


async def test_full_integration():
    """Test complete integration with real portfolio data."""
    print("\n=== Testing Full AI Analytical Reasoning Integration ===\n")

    async with get_async_session() as db:
        # Get first demo portfolio
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("ERROR: No portfolios found in database")
            return

        print(f"Testing with: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}\n")

        # Run investigation with unique focus to avoid cache
        print("Running Claude investigation with real portfolio data...")
        print("Focus: portfolio_overview\n")

        insight = await analytical_reasoning_service.investigate_portfolio(
            db=db,
            portfolio_id=portfolio.id,
            insight_type=InsightType.DAILY_SUMMARY,
            focus_area="portfolio_overview",  # Unique focus
        )

        print(f"\n{'='*80}")
        print(f"INVESTIGATION COMPLETE")
        print(f"{'='*80}\n")

        print(f"Title: {insight.title}")
        print(f"Severity: {insight.severity}\n")

        print(f"Summary:")
        print(f"{insight.summary}\n")

        print(f"Key Findings:")
        for i, finding in enumerate((insight.key_findings or []), 1):
            print(f"{i}. {finding}")

        print(f"\nRecommendations:")
        for i, rec in enumerate((insight.recommendations or []), 1):
            print(f"{i}. {rec}")

        print(f"\nData Limitations:")
        print(f"{insight.data_limitations}\n")

        print(f"{'='*80}")
        print(f"PERFORMANCE METRICS")
        print(f"{'='*80}")
        print(f"Model: {insight.model_used}")
        print(f"Provider: {insight.provider}")
        print(f"Cost: ${insight.cost_usd:.4f}")
        print(f"Time: {insight.generation_time_ms / 1000:.1f}s")
        print(f"Tokens In: {insight.token_count_input}")
        print(f"Tokens Out: {insight.token_count_output}")
        print(f"Total Tokens: {insight.token_count_input + insight.token_count_output}")

        print(f"\n{'='*80}")
        print(f"Test Complete!")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(test_full_integration())
