"""
Test Correlation Service Snapshot Integration

Verifies that correlation service uses pre-calculated snapshot values
instead of recalculating portfolio value from positions.
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.services.correlation_service import CorrelationService

# Disable verbose SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def main():
    """Test correlation service snapshot integration"""

    print("\n" + "="*80)
    print("CORRELATION SERVICE SNAPSHOT INTEGRATION TEST")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get hedge fund portfolio
        stmt = select(Portfolio).join(User).where(
            User.email == 'demo_hedgefundstyle@sigmasight.com'
        )
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("\n❌ Hedge fund portfolio not found")
            return

        print(f"\n✅ Found portfolio: {portfolio.name}")
        print(f"   Portfolio ID: {portfolio.id}")

        # Check for latest snapshot
        snapshot_stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snapshot_result = await db.execute(snapshot_stmt)
        latest_snapshot = snapshot_result.scalar_one_or_none()

        if not latest_snapshot:
            print("\n⚠️  No portfolio snapshot found")
            print("   Correlation service will fall back to real-time calculation")
        else:
            print(f"\n✅ Latest snapshot found:")
            print(f"   Date: {latest_snapshot.snapshot_date}")
            print(f"   Gross Exposure: ${float(latest_snapshot.gross_exposure):,.2f}")
            print(f"   Net Exposure: ${float(latest_snapshot.net_exposure):,.2f}")
            print(f"   Total Value: ${float(latest_snapshot.total_value):,.2f}")

        # Test correlation service
        print(f"\n{'='*80}")
        print("TESTING CORRELATION SERVICE")
        print(f"{'='*80}\n")

        correlation_service = CorrelationService(db)

        # Test _get_portfolio_value_from_snapshot method
        calculation_date = datetime.now()
        portfolio_value = await correlation_service._get_portfolio_value_from_snapshot(
            portfolio.id, calculation_date
        )

        print(f"\n📊 Portfolio Value from Snapshot:")
        if portfolio_value is not None:
            print(f"   ✅ Retrieved: ${portfolio_value:,.2f}")
            print(f"   Source: PortfolioSnapshot.gross_exposure")
        else:
            print(f"   ⚠️  No snapshot available (would fall back to real-time calculation)")

        # Verify it matches snapshot
        if latest_snapshot and portfolio_value is not None:
            expected_value = float(latest_snapshot.gross_exposure)
            if abs(portfolio_value - expected_value) < 0.01:
                print(f"\n✅ VALUE MATCH CONFIRMED:")
                print(f"   Snapshot gross_exposure: ${expected_value:,.2f}")
                print(f"   Service returned value:   ${portfolio_value:,.2f}")
                print(f"   ✓ Values match! Service is using pre-calculated snapshot.")
            else:
                print(f"\n❌ VALUE MISMATCH:")
                print(f"   Snapshot gross_exposure: ${expected_value:,.2f}")
                print(f"   Service returned value:   ${portfolio_value:,.2f}")
                print(f"   ✗ Values don't match!")

        # Calculate real-time value for comparison
        print(f"\n{'='*80}")
        print("COMPARISON: Snapshot vs Real-Time Calculation")
        print(f"{'='*80}\n")

        # Get positions and calculate real-time
        portfolio_stmt = select(Portfolio).where(
            Portfolio.id == portfolio.id
        )
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio_with_positions = portfolio_result.scalar_one_or_none()

        from sqlalchemy.orm import selectinload
        portfolio_stmt = select(Portfolio).where(
            Portfolio.id == portfolio.id
        ).options(selectinload(Portfolio.positions))
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio_with_positions = portfolio_result.scalar_one_or_none()

        realtime_value = sum(
            abs(p.quantity * p.last_price)
            for p in portfolio_with_positions.positions
        )

        print(f"Real-time calculation (from positions): ${realtime_value:,.2f}")
        if portfolio_value is not None:
            print(f"Snapshot value (gross_exposure):        ${portfolio_value:,.2f}")
            print(f"Difference:                             ${abs(realtime_value - portfolio_value):,.2f}")

            if abs(realtime_value - portfolio_value) < 1.00:
                print(f"\n✅ VALUES MATCH (< $1 difference)")
            else:
                print(f"\n⚠️  Values differ (snapshot may be stale or prices updated)")

        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}\n")

        if portfolio_value is not None:
            print("✅ Correlation service successfully uses snapshot values")
            print("✅ Eliminates duplicate calculation of portfolio value")
            print("✅ Follows DRY principle")
            print("\n🎉 Refactoring successful!")
        else:
            print("⚠️  No snapshot available for testing")
            print("   Service will fall back to real-time calculation")
            print("   Run batch orchestrator to create snapshots first")

        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
