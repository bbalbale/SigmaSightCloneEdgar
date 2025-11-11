"""Diagnose leverage calculation for Individual Investor portfolio"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot

async def diagnose():
    # Individual Investor portfolio ID
    indiv_id = '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe'

    async with AsyncSessionLocal() as db:
        # Get portfolio
        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.id == indiv_id)
        )
        portfolio = portfolio_result.scalar_one()

        # Get latest snapshot
        snapshot_result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == indiv_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snapshot = snapshot_result.scalar_one_or_none()

        # Get positions
        positions_result = await db.execute(
            select(Position).where(Position.portfolio_id == indiv_id)
        )
        positions = positions_result.scalars().all()

        print("=" * 80)
        print("INDIVIDUAL INVESTOR PORTFOLIO - LEVERAGE DIAGNOSIS")
        print("=" * 80)
        print()

        # Calculate from positions
        long_mv = 0.0
        short_mv = 0.0

        for pos in positions:
            quantity = float(pos.quantity) if pos.quantity else 0.0
            last_price = float(pos.last_price or 0.0)
            position_value = quantity * last_price

            if quantity > 0:
                long_mv += position_value
            else:
                short_mv += position_value  # Will be negative

        gross_exposure = long_mv + abs(short_mv)
        net_exposure = long_mv + short_mv

        print("FROM POSITIONS:")
        print(f"  Long Market Value:  ${long_mv:,.2f}")
        print(f"  Short Market Value: ${short_mv:,.2f}")
        print(f"  Gross Exposure:     ${gross_exposure:,.2f}")
        print(f"  Net Exposure:       ${net_exposure:,.2f}")
        print()

        print("FROM SNAPSHOT:")
        if snapshot:
            print(f"  Snapshot Date:      {snapshot.snapshot_date}")
            print(f"  Equity Balance:     ${float(snapshot.equity_balance):,.2f}")
            print(f"  Total Value:        ${float(snapshot.total_value):,.2f}")
            print(f"  Cash Value:         ${float(snapshot.cash_value):,.2f}")
            print(f"  Long Value:         ${float(snapshot.long_value):,.2f}")
            print(f"  Short Value:        ${float(snapshot.short_value):,.2f}")
            print(f"  Gross Exposure:     ${float(snapshot.gross_exposure):,.2f}")
        print()

        # Current calculation
        equity_balance = float(snapshot.equity_balance) if snapshot else float(portfolio.equity_balance)
        cash_balance = equity_balance - long_mv + abs(short_mv)
        leverage = gross_exposure / equity_balance if equity_balance > 0 else 0.0

        print("CURRENT CALCULATION:")
        print(f"  Equity Balance:     ${equity_balance:,.2f}")
        print(f"  Calculated Cash:    ${cash_balance:,.2f}")
        print(f"  Leverage:           {leverage:.2f}x")
        print()

        print("ANALYSIS:")
        if abs(short_mv) > 0:
            print("  ⚠️  Portfolio has SHORT positions")
        else:
            print("  ✅ Portfolio is LONG ONLY")

        if leverage > 1.01:
            print(f"  ⚠️  Leverage {leverage:.2f}x indicates borrowed capital")
            print(f"      Gross exposure (${gross_exposure:,.2f}) > Equity (${equity_balance:,.2f})")
        elif leverage > 0.99:
            print(f"  ✅ Fully invested (leverage ≈ 1.0)")
        else:
            print(f"  ✅ Partially invested (leverage = {leverage:.2f}x)")

        if cash_balance < 0:
            print(f"  ❌ NEGATIVE CASH: ${cash_balance:,.2f}")
            print(f"      This suggests calculation error!")

        print()
        print("EXPECTED BEHAVIOR:")
        print("  - Long-only portfolio with no margin should have leverage ≤ 1.0")
        print("  - Leverage = Gross Exposure / Equity Balance")
        print("  - If Long MV > Equity, that means negative cash (using margin)")
        print("=" * 80)

asyncio.run(diagnose())
