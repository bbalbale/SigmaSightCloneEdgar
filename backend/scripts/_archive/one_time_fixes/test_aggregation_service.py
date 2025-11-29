"""
Integration test for PortfolioAggregationService

Tests the service against real database with demo data.
"""
import asyncio
from uuid import UUID
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User
from app.services.portfolio_aggregation_service import PortfolioAggregationService


async def test_aggregation_service():
    """Test the aggregation service with demo user."""
    async with get_async_session() as db:
        # Get demo user
        result = await db.execute(
            select(User).where(User.email == 'demo_individual@sigmasight.com')
        )
        user = result.scalar_one_or_none()

        if not user:
            print("ERROR: Demo user not found")
            return

        print(f"Testing with user: {user.email}")
        print(f"User ID: {user.id}")

        # Create service
        service = PortfolioAggregationService(db)

        # Test 1: Get user portfolios
        print("\n--- Test 1: Get User Portfolios ---")
        portfolios = await service.get_user_portfolios(user.id)
        print(f"Found {len(portfolios)} portfolios:")
        for p in portfolios:
            print(f"  - {p.account_name} ({p.account_type})")

        # Test 2: Get portfolio values
        print("\n--- Test 2: Get Portfolio Values ---")
        portfolio_ids = [p.id for p in portfolios]
        values = await service.get_portfolio_values(portfolio_ids)
        print("Portfolio values:")
        for portfolio in portfolios:
            value = values.get(portfolio.id, 0)
            print(f"  - {portfolio.account_name}: ${value:,.2f}")

        # Test 3: Calculate weights
        print("\n--- Test 3: Calculate Weights ---")
        weights = service.calculate_weights(values)
        print("Portfolio weights:")
        for portfolio in portfolios:
            weight = weights.get(portfolio.id, 0)
            print(f"  - {portfolio.account_name}: {weight:.1%}")

        # Test 4: Aggregate portfolio metrics
        print("\n--- Test 4: Aggregate Portfolio Metrics ---")
        result = await service.aggregate_portfolio_metrics(user.id)
        print(f"Portfolio count: {result['portfolio_count']}")
        print(f"Total value: ${result['total_value']:,.2f}")
        print("\nPortfolio breakdown:")
        for p in result['portfolios']:
            print(f"  - {p['account_name']}: ${p['value']:,.2f} ({p['weight']:.1%})")

        # Test 5: Test weighted average calculation
        print("\n--- Test 5: Test Weighted Average (Beta) ---")
        # Simulate portfolio betas
        portfolio_metrics = {
            portfolios[0].id: {'beta': 1.2, 'weight': weights.get(portfolios[0].id, 0)}
        }
        if len(portfolios) > 1:
            # If user somehow has multiple portfolios, include them
            for i, p in enumerate(portfolios[1:], 1):
                portfolio_metrics[p.id] = {
                    'beta': 0.9 + (i * 0.1),  # Simulated betas
                    'weight': weights.get(p.id, 0)
                }

        aggregate_beta = await service.aggregate_beta(portfolio_metrics)
        if aggregate_beta:
            print(f"Aggregate beta: {aggregate_beta:.4f}")
        else:
            print("No beta data available")

        print("\n=== All tests completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(test_aggregation_service())
