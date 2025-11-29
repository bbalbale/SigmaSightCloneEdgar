"""
Fix position classification mismatches by directly updating the database
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy import select, update
from app.database import get_async_session
from app.models.positions import Position
from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

async def fix_position_classifications():
    """Fix misclassified positions by updating their investment_class"""

    # Define private patterns
    private_patterns = [
        'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',
        'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET'
    ]

    async with get_async_session() as db:
        # Get all positions
        result = await db.execute(select(Position))
        positions = result.scalars().all()

        fixed_count = 0
        logger.info("\nChecking positions for classification issues...")

        for pos in positions:
            # Determine correct investment class
            symbol_upper = pos.symbol.upper()

            # Check if it should be PRIVATE
            should_be_private = any(pattern in symbol_upper for pattern in private_patterns)

            # Check if it looks like an option (simplified check)
            looks_like_option = (
                len(pos.symbol) > 15 and
                (pos.symbol[-9] in ['C', 'P'] or pos.symbol[-8] in ['C', 'P']) and
                pos.symbol[6:12].isdigit()  # Has date portion
            )

            # Determine correct classification
            if should_be_private:
                correct_class = 'PRIVATE'
            elif looks_like_option:
                correct_class = 'OPTIONS'
            else:
                correct_class = 'PUBLIC'

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

        # Check for any remaining issues
        issues_found = []
        for pos in positions:
            symbol_upper = pos.symbol.upper()
            is_private_pattern = any(pattern in symbol_upper for pattern in private_patterns)

            if is_private_pattern and pos.investment_class != 'PRIVATE':
                issues_found.append(f"{pos.symbol} (classified as {pos.investment_class}, should be PRIVATE)")

        if issues_found:
            logger.error(f"\nStill have {len(issues_found)} issues:")
            for issue in issues_found:
                logger.error(f"  - {issue}")
        else:
            logger.info("\nAll positions are correctly classified!")

if __name__ == "__main__":
    asyncio.run(fix_position_classifications())
