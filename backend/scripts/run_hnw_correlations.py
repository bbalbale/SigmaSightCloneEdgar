"""
Run correlation calculation for High Net Worth portfolio
"""
import asyncio
from datetime import datetime
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.services.correlation_service import CorrelationService
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get High Net Worth portfolio
        stmt = select(Portfolio).join(User).where(
            User.email == 'demo_hnw@sigmasight.com'
        )
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("❌ Portfolio not found")
            return

        print(f"✅ Found portfolio: {portfolio.name}")
        print(f"   ID: {portfolio.id}")

        # Run correlation calculation
        print(f"\n🔄 Running correlation calculation...")
        correlation_service = CorrelationService(db)

        calculation = await correlation_service.calculate_portfolio_correlations(
            portfolio_id=portfolio.id,
            calculation_date=datetime.now(),
            force_recalculate=True,
            duration_days=90
        )

        if calculation:
            print(f"\n✅ Correlation calculation completed:")
            print(f"   Calculation ID: {calculation.id}")
            print(f"   Overall correlation: {float(calculation.overall_correlation):.4f}")
            print(f"   Effective positions: {float(calculation.effective_positions):.2f}")
            print(f"   Positions included: {calculation.positions_included}")
            print(f"   Positions excluded: {calculation.positions_excluded}")
        else:
            print(f"\n⚠️  Correlation calculation returned None (likely all PRIVATE positions)")

if __name__ == "__main__":
    asyncio.run(main())
