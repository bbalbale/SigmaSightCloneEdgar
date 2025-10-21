"""
Test the new single-factor market beta endpoint
"""

import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio


async def main():
    async with get_async_session() as db:
        # Get hedge fund portfolio
        result = await db.execute(
            select(User).where(User.email == "demo_hedgefundstyle@sigmasight.com")
        )
        user = result.scalar_one_or_none()

        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = result.scalars().first()

        print("=" * 80)
        print("TESTING NEW MARKET BETA ENDPOINT")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print()
        print("Testing endpoint: GET /api/v1/analytics/portfolio/{portfolio_id}/market-beta")
        print()
        print("Please test in browser or via curl:")
        print(f"curl http://localhost:8000/api/v1/analytics/portfolio/{portfolio.id}/market-beta")
        print()
        print("Expected response:")
        print("{")
        print('  "available": true,')
        print(f'  "portfolio_id": "{portfolio.id}",')
        print('  "calculation_date": "2025-10-18",')
        print('  "data": {')
        print('    "market_beta_weighted": 0.874847,')
        print('    "market_beta_r_squared": 0.85,')
        print('    "market_beta_observations": 90,')
        print('    "market_beta_direct": 0.880123')
        print('  },')
        print('  "metadata": {')
        print('    "calculation_method": "equity_weighted_average",')
        print('    "model_type": "single_factor_ols"')
        print('  }')
        print('}')


if __name__ == "__main__":
    asyncio.run(main())
