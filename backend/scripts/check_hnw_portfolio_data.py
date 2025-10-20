"""
Check what data Claude received for the HNW portfolio analysis.
"""
import asyncio
from uuid import UUID
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position
from sqlalchemy import select, desc


async def check_data():
    async with get_async_session() as db:
        # Get the HNW portfolio
        result = await db.execute(
            select(Portfolio).where(Portfolio.name.like('%High Net Worth%'))
        )
        portfolio = result.scalar_one()

        print(f'Portfolio: {portfolio.name}')
        print(f'Portfolio ID: {portfolio.id}')
        print(f'Equity Balance (from Portfolio model): ${portfolio.equity_balance:,.2f}')
        print()

        # Get latest snapshot
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()

        if snapshot:
            print(f'=== LATEST SNAPSHOT ===')
            print(f'Snapshot Date: {snapshot.snapshot_date}')
            print(f'Total Value: ${snapshot.total_value:,.2f}')
            print(f'Cash Value: ${snapshot.cash_value:,.2f}' if snapshot.cash_value else 'Cash Value: None')
            print(f'Long Value: ${snapshot.long_value:,.2f}' if snapshot.long_value else 'Long Value: None')
            print(f'Short Value: ${snapshot.short_value:,.2f}' if snapshot.short_value else 'Short Value: None')
            print(f'Gross Exposure: ${snapshot.gross_exposure:,.2f}' if snapshot.gross_exposure else 'Gross Exposure: None')
            print(f'Net Exposure: ${snapshot.net_exposure:,.2f}' if snapshot.net_exposure else 'Net Exposure: None')
            print(f'Daily P&L: ${snapshot.daily_pnl:,.2f}' if snapshot.daily_pnl else 'Daily P&L: None')
            print(f'Cumulative P&L: ${snapshot.cumulative_pnl:,.2f}' if snapshot.cumulative_pnl else 'Cumulative P&L: None')
            print()

            # Calculate what Claude saw
            equity_balance = float(portfolio.equity_balance)
            total_value = float(snapshot.total_value)
            difference = equity_balance - total_value
            pct_diff = (difference / equity_balance) * 100

            print(f'=== CLAUDE\'S COMPARISON ===')
            print(f'Equity Balance: ${equity_balance:,.2f}')
            print(f'Total Value: ${total_value:,.2f}')
            print(f'Difference: ${difference:,.2f}')
            print(f'Percentage: {pct_diff:.1f}%')
            print()
        else:
            print('No snapshot found!')

        # Check positions for actual P&L
        result = await db.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )
        positions = result.scalars().all()

        total_unrealized = sum(float(p.unrealized_pnl or 0) for p in positions)
        total_realized = sum(float(p.realized_pnl or 0) for p in positions)
        total_market_value = sum(float(p.market_value or 0) for p in positions)

        print(f'=== POSITION DATA ===')
        print(f'Number of positions: {len(positions)}')
        print(f'Total Market Value: ${total_market_value:,.2f}')
        print(f'Total Unrealized P&L: ${total_unrealized:,.2f}')
        print(f'Total Realized P&L: ${total_realized:,.2f}')
        print(f'Total P&L: ${total_unrealized + total_realized:,.2f}')
        print()

        # Show top 5 winners and losers
        sorted_positions = sorted(positions, key=lambda p: float(p.unrealized_pnl or 0), reverse=True)

        print(f'=== TOP 5 WINNERS ===')
        for pos in sorted_positions[:5]:
            pnl = float(pos.unrealized_pnl or 0)
            if pnl > 0:
                print(f'{pos.symbol}: ${pnl:,.2f}')

        print()
        print(f'=== TOP 5 LOSERS ===')
        for pos in reversed(sorted_positions[-5:]):
            pnl = float(pos.unrealized_pnl or 0)
            if pnl < 0:
                print(f'{pos.symbol}: ${pnl:,.2f}')


if __name__ == "__main__":
    asyncio.run(check_data())
