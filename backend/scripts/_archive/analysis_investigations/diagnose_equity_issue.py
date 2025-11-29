"""
Comprehensive diagnosis of equity balance issue

This script will check:
1. Portfolio.equity_balance (initial capital - should NOT change)
2. PortfolioSnapshot.equity_balance (rolling balance - SHOULD change with P&L)
3. Daily P&L calculations
4. Whether snapshots are being created
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position
from decimal import Decimal


async def diagnose():
    async with get_async_session() as db:
        print("=" * 80)
        print("EQUITY BALANCE DIAGNOSTIC")
        print("=" * 80)
        print()

        # Get all portfolios
        portfolios_query = select(Portfolio).where(Portfolio.deleted_at.is_(None))
        portfolios_result = await db.execute(portfolios_query)
        portfolios = portfolios_result.scalars().all()

        for portfolio in portfolios:
            print(f"\n{'=' * 80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"ID: {portfolio.id}")
            print(f"{'=' * 80}")

            # 1. Check initial equity balance
            print(f"\n1. INITIAL EQUITY BALANCE (Portfolio.equity_balance)")
            print(f"   This should remain constant (initial capital):")
            if portfolio.equity_balance:
                print(f"   ${portfolio.equity_balance:,.2f}")
            else:
                print(f"   ⚠️  NOT SET - This is a problem!")

            # 2. Check snapshots
            print(f"\n2. PORTFOLIO SNAPSHOTS (PortfolioSnapshot.equity_balance)")
            print(f"   This should change daily with P&L:")

            snapshots_query = (
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(10)
            )
            snapshots_result = await db.execute(snapshots_query)
            snapshots = snapshots_result.scalars().all()

            if not snapshots:
                print(f"   ⚠️  NO SNAPSHOTS FOUND - This is the problem!")
                print(f"   Snapshots need to be created by running batch processing.")
            else:
                print(f"   Found {len(snapshots)} recent snapshots:")
                print(f"\n   {'Date':<12} {'Total Value':>15} {'Daily P&L':>15} {'Equity Balance':>18}")
                print(f"   {'-' * 12} {'-' * 15} {'-' * 15} {'-' * 18}")

                for snapshot in snapshots:
                    total_val = f"${snapshot.total_value:,.2f}" if snapshot.total_value else "N/A"
                    daily_pnl = f"${snapshot.daily_pnl:,.2f}" if snapshot.daily_pnl else "N/A"
                    equity_bal = f"${snapshot.equity_balance:,.2f}" if snapshot.equity_balance else "⚠️  NOT SET"

                    print(f"   {snapshot.snapshot_date} {total_val:>15} {daily_pnl:>15} {equity_bal:>18}")

                # Check if equity_balance is being updated
                recent_snapshot = snapshots[0]
                if recent_snapshot.equity_balance is None:
                    print(f"\n   ❌ PROBLEM: Snapshot equity_balance is NULL!")
                    print(f"   This means P&L calculator is not updating equity_balance.")
                elif portfolio.equity_balance and abs(recent_snapshot.equity_balance - portfolio.equity_balance) < 0.01:
                    print(f"\n   ❌ PROBLEM: Equity balance hasn't changed from initial!")
                    print(f"   Initial: ${portfolio.equity_balance:,.2f}")
                    print(f"   Current: ${recent_snapshot.equity_balance:,.2f}")
                    print(f"   These should be different if P&L has occurred.")
                else:
                    print(f"\n   ✅ Equity balance is changing (good!)")
                    if portfolio.equity_balance:
                        change = recent_snapshot.equity_balance - portfolio.equity_balance
                        print(f"   Initial: ${portfolio.equity_balance:,.2f}")
                        print(f"   Current: ${recent_snapshot.equity_balance:,.2f}")
                        print(f"   Change: ${change:,.2f}")

            # 3. Check positions and current market values
            print(f"\n3. CURRENT POSITIONS")
            positions_query = (
                select(Position)
                .where(and_(
                    Position.portfolio_id == portfolio.id,
                    Position.deleted_at.is_(None)
                ))
            )
            positions_result = await db.execute(positions_query)
            positions = positions_result.scalars().all()

            if positions:
                total_current_value = Decimal('0')
                total_cost_basis = Decimal('0')

                print(f"   Found {len(positions)} positions:")
                print(f"\n   {'Symbol':<10} {'Qty':>8} {'Entry':>10} {'Current':>10} {'Cost Basis':>15} {'Market Value':>15}")
                print(f"   {'-' * 10} {'-' * 8} {'-' * 10} {'-' * 10} {'-' * 15} {'-' * 15}")

                for pos in positions[:10]:  # Show first 10
                    cost_basis = pos.entry_price * pos.quantity
                    market_value = pos.market_value or (pos.current_price * pos.quantity if pos.current_price else cost_basis)

                    total_cost_basis += cost_basis
                    total_current_value += market_value

                    print(f"   {pos.symbol:<10} {pos.quantity:>8} ${pos.entry_price:>9.2f} "
                          f"${pos.current_price or 0:>9.2f} ${cost_basis:>14,.2f} ${market_value:>14,.2f}")

                if len(positions) > 10:
                    print(f"   ... and {len(positions) - 10} more positions")

                print(f"\n   Total Cost Basis:  ${total_cost_basis:,.2f}")
                print(f"   Total Market Value: ${total_current_value:,.2f}")
                print(f"   Unrealized P&L:    ${total_current_value - total_cost_basis:,.2f}")

                # Compare with snapshot
                if snapshots:
                    recent_snapshot = snapshots[0]
                    print(f"\n   Snapshot Total Value: ${recent_snapshot.total_value:,.2f}")
                    if abs(recent_snapshot.total_value - total_current_value) > 1.0:
                        print(f"   ⚠️  Mismatch between position sum and snapshot!")
            else:
                print(f"   No positions found")

            print(f"\n{'=' * 80}\n")

        # Summary
        print(f"\n{'=' * 80}")
        print("DIAGNOSTIC SUMMARY")
        print(f"{'=' * 80}")
        print(f"\nKey Concepts:")
        print(f"1. Portfolio.equity_balance = INITIAL CAPITAL (does not change)")
        print(f"2. PortfolioSnapshot.equity_balance = ROLLING BALANCE (changes daily)")
        print(f"3. Rolling balance = Previous equity + Daily P&L")
        print(f"\nIf snapshots are missing or equity_balance is NULL in snapshots:")
        print(f"   → Run batch processing to create snapshots with equity rollforward")
        print(f"\nIf equity_balance in snapshots equals initial equity:")
        print(f"   → P&L calculator may not be running correctly")
        print(f"{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(diagnose())
