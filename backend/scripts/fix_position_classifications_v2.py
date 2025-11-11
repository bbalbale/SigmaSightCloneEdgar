"""
Fix position classification mismatches using proper detection logic
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy import select
from app.database import get_async_session
from app.models.positions import Position
from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

def determine_correct_investment_class(symbol: str) -> str:
    """Determine correct investment class from symbol using same logic as seed script"""

    # Check for private investment patterns FIRST
    # This prevents private symbols with 'C' or 'P' from being misclassified as options
    private_patterns = [
        'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',
        'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET'
    ]
    if any(pattern in symbol.upper() for pattern in private_patterns):
        return 'PRIVATE'

    # Check if it's an option - use the SAME logic as seed_demo_portfolios.py
    # Options format: SYMBOL + YYMMDD + C/P + STRIKE (e.g., SPY250919C00460000)
    # Check last 9 chars for C or P (matches the logic in determine_position_type)
    if len(symbol) > 10 and ('C' in symbol[-9:] or 'P' in symbol[-9:]):
        return 'OPTIONS'

    # Everything else is public equity
    return 'PUBLIC'

async def fix_position_classifications():
    """Fix misclassified positions by updating their investment_class"""

    async with get_async_session() as db:
        # Get all positions
        result = await db.execute(select(Position))
        positions = result.scalars().all()

        fixed_count = 0
        logger.info("\nChecking positions for classification issues...")

        for pos in positions:
            # Determine correct investment class
            correct_class = determine_correct_investment_class(pos.symbol)

            # Fix if misclassified
            if pos.investment_class != correct_class:
                logger.info(f"Fixing {pos.symbol}: {pos.investment_class} -> {correct_class}")
                pos.investment_class = correct_class

                # Also update position_type for private positions if needed
                if correct_class == 'PRIVATE' and pos.position_type.value in ['LC', 'LP', 'SC', 'SP']:
                    from app.models.positions import PositionType
                    # Private positions should be LONG (not option position types)
                    pos.position_type = PositionType.LONG
                    logger.info(f"  Also fixed position_type to LONG")

                fixed_count += 1

        if fixed_count > 0:
            await db.commit()
            logger.info(f"\nFixed {fixed_count} misclassified positions!")
        else:
            logger.info("\nNo misclassifications found - all positions are correctly classified!")

        # Run verification
        logger.info("\nRunning verification...")
        result = await db.execute(select(Position))
        positions = result.scalars().all()

        options_count = sum(1 for p in positions if p.investment_class == 'OPTIONS')
        private_count = sum(1 for p in positions if p.investment_class == 'PRIVATE')
        public_count = sum(1 for p in positions if p.investment_class == 'PUBLIC')

        logger.info(f"\nFinal counts:")
        logger.info(f"  OPTIONS: {options_count}")
        logger.info(f"  PRIVATE: {private_count}")
        logger.info(f"  PUBLIC: {public_count}")
        logger.info(f"  TOTAL: {len(positions)}")

        # Show sample classifications
        logger.info("\nSample classifications:")
        for symbol in ['SPY250919C00460000', 'AAPL250815P00200000', 'CRYPTO_BTC_ETH', 'A16Z_VC_FUND', 'AAPL', 'SPY']:
            result = await db.execute(
                select(Position).where(Position.symbol == symbol)
            )
            pos = result.scalar_one_or_none()
            if pos:
                logger.info(f"  {symbol}: {pos.investment_class}")

        # Check for any remaining issues
        issues_found = []
        private_patterns = [
            'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',
            'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET'
        ]

        for pos in positions:
            symbol_upper = pos.symbol.upper()
            is_private_pattern = any(pattern in symbol_upper for pattern in private_patterns)

            if is_private_pattern and pos.investment_class != 'PRIVATE':
                issues_found.append(f"{pos.symbol} (classified as {pos.investment_class}, should be PRIVATE)")

            # Check for options that might be misclassified
            has_option_marker = 'C' in pos.symbol[-9:] or 'P' in pos.symbol[-9:]
            if len(pos.symbol) > 10 and has_option_marker and not is_private_pattern and pos.investment_class != 'OPTIONS':
                issues_found.append(f"{pos.symbol} (classified as {pos.investment_class}, should be OPTIONS)")

        if issues_found:
            logger.error(f"\nStill have {len(issues_found)} issues:")
            for issue in issues_found:
                logger.error(f"  - {issue}")
        else:
            logger.info("\nAll positions are correctly classified!")

if __name__ == "__main__":
    asyncio.run(fix_position_classifications())
