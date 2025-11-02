"""Debug script to test exposure calculation with logging"""
import asyncio
import logging
from uuid import UUID
from app.database import get_async_session
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from sqlalchemy import select
from app.models.users import Portfolio

# Enable debug logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

async def test_with_logging():
    async with get_async_session() as db:
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()

        print(f'\n=== Testing Portfolio: {portfolio.name} ===')
        print(f'Portfolio ID: {portfolio.id}')
        print(f'Equity Balance: ${portfolio.equity_balance:,.2f}\n')

        service = PortfolioAnalyticsService()
        overview = await service.get_portfolio_overview(db, portfolio.id)

        print(f'\n=== API Response ===')
        print(f'Exposures returned:')
        print(f'  Long:  ${overview["exposures"]["long_exposure"]:,.2f}')
        print(f'  Short: ${overview["exposures"]["short_exposure"]:,.2f}')
        print(f'  Gross: ${overview["exposures"]["gross_exposure"]:,.2f}')
        print(f'  Net:   ${overview["exposures"]["net_exposure"]:,.2f}')
        print(f'\nPosition counts:')
        print(f'  Total: {overview["position_count"]["total_positions"]}')
        print(f'  Long:  {overview["position_count"]["long_count"]}')
        print(f'  Short: {overview["position_count"]["short_count"]}')

if __name__ == "__main__":
    asyncio.run(test_with_logging())
