#!/usr/bin/env python
"""
Update classification to properly identify PRIVATE positions.
According to the Ben Mock Portfolios doc, Portfolio 2 should have:
- Private Equity: Blackstone BX Fund
- Venture Capital: Andreessen Horowitz Fund
- Private REIT: Starwood Real Estate
- Hedge Fund: Two Sigma Spectrum
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.users import Portfolio, User
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger(__name__)


async def update_private_classifications():
    """Update positions that should be classified as PRIVATE."""
    async with AsyncSessionLocal() as db:
        # Get Portfolio 2 (High Net Worth)
        # First try to find by portfolio name
        result = await db.execute(
            select(Portfolio).where(
                Portfolio.name.like('%High%') | Portfolio.name.like('%HNW%') |
                Portfolio.name.like('%Sophisticated%') | Portfolio.name.like('%Net Worth%')
            )
        )
        high_net_worth_portfolio = result.scalar_one_or_none()

        if not high_net_worth_portfolio:
            logger.warning("Could not find High Net Worth portfolio")
            # Try another approach - get all portfolios and check
            result = await db.execute(select(Portfolio))
            portfolios = result.scalars().all()
            logger.info("Available portfolios:")
            for p in portfolios:
                logger.info(f"  - {p.name} (ID: {p.id})")
            return

        logger.info(f"Found High Net Worth portfolio: {high_net_worth_portfolio.name} (ID: {high_net_worth_portfolio.id})")

        # Private investment symbols that should exist based on the documentation
        # These might be represented differently in the actual database
        private_symbols = [
            'BLACKSTONE_BX',
            'BX_FUND',
            'ANDREESSEN_HOROWITZ',
            'AH_FUND',
            'STARWOOD_REIT',
            'TWO_SIGMA',
            'PRIVATE_EQUITY_1',
            'PRIVATE_VC_1',
            'PRIVATE_REIT_1',
            'HEDGE_FUND_1'
        ]

        # Also check for alternative investments that should be classified differently
        alternative_symbols = ['GLD', 'DJP', 'BTC', 'ETH', 'CRYPTO']

        # Get positions for high net worth portfolio
        result = await db.execute(
            select(Position).where(Position.portfolio_id == high_net_worth_portfolio.id)
        )
        hnw_positions = result.scalars().all()

        logger.info(f"\nHigh Net Worth Portfolio has {len(hnw_positions)} positions:")

        updated_count = 0
        for pos in hnw_positions:
            symbol_upper = pos.symbol.upper()

            # Check if this should be a private investment
            is_private = False
            for private_pattern in private_symbols:
                if private_pattern in symbol_upper or symbol_upper in private_pattern:
                    is_private = True
                    break

            # Also check common private investment patterns
            if not is_private and any(pattern in symbol_upper for pattern in ['PRIVATE', 'FUND', 'PE_', 'VC_', 'HF_']):
                is_private = True

            if is_private and pos.investment_class != 'PRIVATE':
                logger.info(f"  Updating {pos.symbol} from {pos.investment_class} to PRIVATE")
                pos.investment_class = 'PRIVATE'
                pos.investment_subtype = determine_private_subtype(pos.symbol)
                updated_count += 1

            # Check alternatives
            elif any(alt in symbol_upper for alt in alternative_symbols):
                if pos.investment_class != 'ALTERNATIVES':
                    logger.info(f"  Updating {pos.symbol} from {pos.investment_class} to ALTERNATIVES")
                    pos.investment_class = 'ALTERNATIVES'
                    pos.investment_subtype = 'COMMODITY' if 'GLD' in symbol_upper or 'DJP' in symbol_upper else 'CRYPTO'
                    updated_count += 1

        if updated_count > 0:
            await db.commit()
            logger.info(f"\n✅ Updated {updated_count} positions")
        else:
            logger.info("\n✅ No positions needed updating")

        # Show final classification summary
        result = await db.execute(
            select(Position).where(Position.portfolio_id == high_net_worth_portfolio.id)
        )
        hnw_positions = result.scalars().all()

        class_summary = {}
        for pos in hnw_positions:
            cls = pos.investment_class or 'UNCLASSIFIED'
            class_summary[cls] = class_summary.get(cls, 0) + 1

        logger.info("\nFinal classification for High Net Worth portfolio:")
        for cls, count in sorted(class_summary.items()):
            logger.info(f"  {cls}: {count} positions")


def determine_private_subtype(symbol: str) -> str:
    """Determine the subtype for a private investment."""
    symbol_upper = symbol.upper()

    if 'PE' in symbol_upper or 'PRIVATE_EQUITY' in symbol_upper or 'BLACKSTONE' in symbol_upper:
        return 'PE_FUND'
    elif 'VC' in symbol_upper or 'VENTURE' in symbol_upper or 'ANDREESSEN' in symbol_upper:
        return 'VC_FUND'
    elif 'REIT' in symbol_upper or 'STARWOOD' in symbol_upper or 'REAL_ESTATE' in symbol_upper:
        return 'PRIVATE_REIT'
    elif 'HF' in symbol_upper or 'HEDGE' in symbol_upper or 'TWO_SIGMA' in symbol_upper:
        return 'HEDGE_FUND'
    elif 'FUND' in symbol_upper:
        return 'FUND'
    else:
        return 'PRIVATE_OTHER'


async def main():
    """Main function."""
    await update_private_classifications()


if __name__ == "__main__":
    asyncio.run(main())