"""
Debug script to investigate which positions are classified as Unclassified
and why PUBLIC stocks are being included.
"""
import asyncio
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.market_data import CompanyProfile
from app.calculations.market_data import get_position_value
from sqlalchemy import select

async def check_unclassified():
    async with AsyncSessionLocal() as db:
        # Get High Net Worth portfolio
        stmt = select(Portfolio).where(Portfolio.name == 'Demo High Net Worth Investor Portfolio')
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print('Portfolio not found')
            return

        print(f'Portfolio: {portfolio.name}')
        print(f'Equity Balance: ${portfolio.equity_balance:,.0f}')
        print()

        # Get active positions
        stmt = select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.exit_date.is_(None)
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()

        print(f'Total Active Positions: {len(positions)}')
        print()

        # Check each position for sector data
        public_without_sector = []
        private_positions = []
        public_with_sector = []

        for pos in positions:
            # Get sector from company_profiles
            stmt = select(CompanyProfile).where(CompanyProfile.symbol == pos.symbol.upper())
            result = await db.execute(stmt)
            profile = result.scalar_one_or_none()

            sector = profile.sector if profile else None
            market_value = abs(float(get_position_value(pos, signed=False)))

            if pos.investment_class == 'PUBLIC':
                if sector and sector != 'Unknown':
                    public_with_sector.append((pos.symbol, sector, market_value))
                else:
                    public_without_sector.append((pos.symbol, pos.investment_class, market_value))
            else:
                private_positions.append((pos.symbol, pos.investment_class, market_value))

        print('=== PUBLIC POSITIONS WITHOUT SECTOR DATA ===')
        total_public_no_sector = 0
        for symbol, inv_class, value in public_without_sector:
            print(f'{symbol:8} | {inv_class:8} | ${value:>12,.0f}')
            total_public_no_sector += value
        print(f'Total: ${total_public_no_sector:,.0f}')
        print()

        print('=== PRIVATE/OPTIONS POSITIONS (Expected Unclassified) ===')
        total_private = 0
        for symbol, inv_class, value in private_positions:
            print(f'{symbol:8} | {inv_class:8} | ${value:>12,.0f}')
            total_private += value
        print(f'Total: ${total_private:,.0f}')
        print()

        print('=== PUBLIC POSITIONS WITH SECTOR DATA ===')
        total_public_with_sector = 0
        for symbol, sector, value in public_with_sector:
            print(f'{symbol:8} | {sector:25} | ${value:>12,.0f}')
            total_public_with_sector += value
        print(f'Total: ${total_public_with_sector:,.0f}')
        print()

        print('=== SUMMARY ===')
        print(f'PUBLIC with sector:    ${total_public_with_sector:>12,.0f}')
        print(f'PUBLIC without sector: ${total_public_no_sector:>12,.0f}')
        print(f'PRIVATE/OPTIONS:       ${total_private:>12,.0f}')
        total_all = total_public_with_sector + total_public_no_sector + total_private
        print(f'Total:                 ${total_all:>12,.0f}')
        print()
        print(f'Current Unclassified (PUBLIC w/o sector + PRIVATE): ${total_public_no_sector + total_private:,.0f} ({((total_public_no_sector + total_private) / portfolio.equity_balance * 100):.1f}%)')
        print(f'Expected Unclassified (PRIVATE only):               ${total_private:,.0f} ({(total_private / portfolio.equity_balance * 100):.1f}%)')

if __name__ == '__main__':
    asyncio.run(check_unclassified())
