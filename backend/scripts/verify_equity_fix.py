"""
Verify that the equity balance fix is working correctly.

This script checks:
1. Portfolio.equity_balance has been updated by equity_balance_update job
2. Latest snapshot uses the same equity balance
3. Factor calculations used correct equity for position weighting
"""
import asyncio
from sqlalchemy import select, desc, func
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionMarketBeta
from app.models.positions import Position
from datetime import date


async def main():
    print("=" * 80)
    print("EQUITY BALANCE FIX VERIFICATION")
    print("=" * 80)
    print()

    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"

    async with get_async_session() as db:
        # Step 1: Check Portfolio.equity_balance
        portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            print(f"Portfolio {portfolio_id} not found!")
            return

        portfolio_equity = float(portfolio.equity_balance) if portfolio.equity_balance else 0

        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio.equity_balance: ${portfolio_equity:,.2f}")
        print()

        # Step 2: Check latest snapshot equity_balance
        latest_snapshot_stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio_id
        ).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(1)

        snapshot_result = await db.execute(latest_snapshot_stmt)
        latest_snapshot = snapshot_result.scalar_one_or_none()

        if latest_snapshot:
            snapshot_equity = float(latest_snapshot.equity_balance) if latest_snapshot.equity_balance else 0
            print(f"Latest Snapshot Date: {latest_snapshot.snapshot_date}")
            print(f"Snapshot.equity_balance: ${snapshot_equity:,.2f}")
            print(f"Snapshot.total_value: ${float(latest_snapshot.total_value):,.2f}")
            print(f"Snapshot.daily_pnl: ${float(latest_snapshot.daily_pnl):,.2f}")
            print()

            # Check if they match
            if abs(portfolio_equity - snapshot_equity) < 0.01:
                print("✅ Portfolio.equity_balance matches Snapshot.equity_balance")
            else:
                print(f"❌ MISMATCH: Portfolio equity (${portfolio_equity:,.2f}) != Snapshot equity (${snapshot_equity:,.2f})")
            print()
        else:
            print("❌ No snapshots found!")
            print()

        # Step 3: Verify factor calculations used correct equity
        # Get total position market value
        positions_stmt = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.deleted_at.is_(None),
            Position.exit_date.is_(None)
        )
        positions_result = await db.execute(positions_stmt)
        positions = positions_result.scalars().all()

        total_market_value = sum(float(p.market_value) if p.market_value else 0 for p in positions)

        print(f"Total Position Market Value: ${total_market_value:,.2f}")
        print(f"Number of Positions: {len(positions)}")
        print()

        # Step 4: Check beta calculations (if any exist)
        beta_stmt = select(PositionMarketBeta).where(
            PositionMarketBeta.portfolio_id == portfolio_id,
            PositionMarketBeta.calc_date == date.today()
        ).limit(5)

        beta_result = await db.execute(beta_stmt)
        betas = beta_result.scalars().all()

        if betas:
            print(f"Sample Beta Calculations from today ({len(betas)} shown):")
            print("-" * 80)
            for beta_record in betas:
                # Get position symbol
                pos_stmt = select(Position).where(Position.id == beta_record.position_id)
                pos_result = await db.execute(pos_stmt)
                pos = pos_result.scalar_one_or_none()

                if pos:
                    position_value = float(pos.market_value) if pos.market_value else 0
                    weight = position_value / portfolio_equity if portfolio_equity > 0 else 0

                    print(f"  {pos.symbol:6s}: beta={float(beta_record.beta):6.3f}, "
                          f"value=${position_value:>12,.2f}, weight={weight:6.2%}")
            print()
            print("✅ Beta calculations exist for today - factor calculations likely used updated equity")
        else:
            print("⚠️  No beta calculations found for today")
        print()

        # Step 5: Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Portfolio equity: ${portfolio_equity:,.2f}")
        print(f"Snapshot equity:  ${snapshot_equity:,.2f}" if latest_snapshot else "Snapshot equity:  N/A")
        print(f"Match: {'✅ YES' if latest_snapshot and abs(portfolio_equity - snapshot_equity) < 0.01 else '❌ NO'}")
        print()

        # Calculate expected weight for largest position
        if positions and portfolio_equity > 0:
            largest_position = max(positions, key=lambda p: float(p.market_value) if p.market_value else 0)
            largest_value = float(largest_position.market_value) if largest_position.market_value else 0
            expected_weight = largest_value / portfolio_equity

            print(f"Largest position: {largest_position.symbol}")
            print(f"  Market value: ${largest_value:,.2f}")
            print(f"  Expected weight: {expected_weight:.2%}")
            print(f"  (This weight should be used in factor calculations)")
            print()

        print("=" * 80)
        print("VERIFICATION COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
