#!/usr/bin/env python
"""
Check for private investment positions in the database.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.users import Portfolio
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger(__name__)


async def find_private_positions():
    """Find positions that should be classified as PRIVATE."""
    async with AsyncSessionLocal() as db:
        # Get all positions
        result = await db.execute(select(Position))
        positions = result.scalars().all()

        logger.info(f"Total positions in database: {len(positions)}")

        # Known private investment patterns from the Ben Mock Portfolios doc
        private_patterns = [
            'BLACKSTONE', 'BX FUND', 'BX_FUND',
            'ANDREESSEN', 'AH_FUND', 'A16Z',
            'STARWOOD', 'STARWOOD_REIT',
            'TWO SIGMA', 'TWO_SIGMA', 'SPECTRUM',
            'PRIVATE', 'FUND', 'PE_', 'VC_', 'HF_',
            'HOME_EQUITY', 'RENTAL', 'CONDO',
            'REAL_ESTATE', 'PROPERTY',
            'GLD', 'DJP',  # Alternatives
            'BITCOIN', 'BTC', 'ETH', 'CRYPTO',
            'ART', 'COLLECTIBLES'
        ]

        potential_private = []
        for pos in positions:
            symbol_upper = pos.symbol.upper()
            # Check if symbol matches any private pattern
            for pattern in private_patterns:
                if pattern in symbol_upper:
                    potential_private.append(pos)
                    break

        logger.info(f"\nFound {len(potential_private)} potential private positions:")
        for pos in potential_private:
            logger.info(f"  - {pos.symbol} (Portfolio: {pos.portfolio_id}, Current class: {pos.investment_class})")

        # Group by portfolio
        portfolios = {}
        for pos in positions:
            if pos.portfolio_id not in portfolios:
                portfolios[pos.portfolio_id] = []
            portfolios[pos.portfolio_id].append(pos)

        # Show portfolio breakdown
        logger.info("\n" + "="*60)
        logger.info("Portfolio Breakdown:")
        for portfolio_id, portfolio_positions in portfolios.items():
            # Get portfolio name
            result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = result.scalar_one_or_none()

            logger.info(f"\nPortfolio: {portfolio.name if portfolio else 'Unknown'} ({portfolio_id})")
            logger.info(f"  Total positions: {len(portfolio_positions)}")

            # Show unique symbols
            symbols = sorted(set(p.symbol for p in portfolio_positions))
            logger.info(f"  Symbols: {', '.join(symbols[:10])}")
            if len(symbols) > 10:
                logger.info(f"           {', '.join(symbols[10:20])}")
            if len(symbols) > 20:
                logger.info(f"           {', '.join(symbols[20:])}")

        return potential_private


async def main():
    """Main function."""
    await find_private_positions()


if __name__ == "__main__":
    asyncio.run(main())