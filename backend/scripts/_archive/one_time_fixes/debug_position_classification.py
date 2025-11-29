"""
Debug script to identify position classification issues
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

async def check_position_classifications():
    """Check all positions and identify misclassifications"""

    async with get_async_session() as db:
        # Get all positions
        result = await db.execute(
            select(Position).order_by(Position.symbol)
        )
        positions = result.scalars().all()

        logger.info(f"\n{'='*80}")
        logger.info(f"POSITION CLASSIFICATION DIAGNOSTIC")
        logger.info(f"{'='*80}\n")

        # Track issues
        options_classified = []
        private_classified = []
        public_classified = []

        for pos in positions:
            # Categorize by investment_class
            if pos.investment_class == 'OPTIONS':
                options_classified.append(pos)
            elif pos.investment_class == 'PRIVATE':
                private_classified.append(pos)
            else:
                public_classified.append(pos)

        # Report OPTIONS positions
        logger.info(f"\n{'='*80}")
        logger.info(f"OPTIONS POSITIONS (investment_class='OPTIONS'): {len(options_classified)}")
        logger.info(f"{'='*80}")

        for pos in options_classified:
            has_underlying = "✓" if pos.underlying_symbol else "✗"
            has_strike = "✓" if pos.strike_price else "✗"
            has_expiry = "✓" if pos.expiration_date else "✗"

            # Check if symbol looks like a real option
            is_likely_option = (
                len(pos.symbol) > 10 and
                (pos.symbol[-9] in ['C', 'P'] or pos.symbol[-8] in ['C', 'P'])
            )

            status = "✓ CORRECT" if is_likely_option else "⚠️  MISCLASSIFIED?"

            logger.info(f"\n  Symbol: {pos.symbol}")
            logger.info(f"    Position Type: {pos.position_type.value}")
            logger.info(f"    Investment Class: {pos.investment_class}")
            logger.info(f"    Has Underlying: {has_underlying} | Strike: {has_strike} | Expiry: {has_expiry}")
            logger.info(f"    Status: {status}")

        # Report PRIVATE positions
        logger.info(f"\n{'='*80}")
        logger.info(f"PRIVATE POSITIONS (investment_class='PRIVATE'): {len(private_classified)}")
        logger.info(f"{'='*80}")

        private_patterns = [
            'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',
            'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET'
        ]

        for pos in private_classified:
            # Check if symbol matches private patterns
            matches_pattern = any(pattern in pos.symbol.upper() for pattern in private_patterns)

            # Check if it has C or P that might cause issues
            has_c_or_p = 'C' in pos.symbol.upper() or 'P' in pos.symbol.upper()

            status = "✓ CORRECT" if matches_pattern else "⚠️  MISCLASSIFIED?"
            warning = " (contains C/P)" if has_c_or_p else ""

            logger.info(f"\n  Symbol: {pos.symbol}")
            logger.info(f"    Position Type: {pos.position_type.value}")
            logger.info(f"    Investment Class: {pos.investment_class}")
            logger.info(f"    Investment Subtype: {pos.investment_subtype or 'N/A'}")
            logger.info(f"    Status: {status}{warning}")

        # Report PUBLIC positions
        logger.info(f"\n{'='*80}")
        logger.info(f"PUBLIC POSITIONS (investment_class='PUBLIC'): {len(public_classified)}")
        logger.info(f"{'='*80}")

        # Just show count for public (should be stocks/ETFs)
        logger.info(f"\n  Total public equity positions: {len(public_classified)}")

        # Summary of potential issues
        logger.info(f"\n{'='*80}")
        logger.info(f"POTENTIAL ISSUES DETECTED")
        logger.info(f"{'='*80}\n")

        # Check for private symbols in options category
        misclassified_as_options = []
        private_patterns = [
            'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',
            'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET'
        ]

        for pos in options_classified:
            if any(pattern in pos.symbol.upper() for pattern in private_patterns):
                misclassified_as_options.append(pos)

        if misclassified_as_options:
            logger.error(f"⚠️  Found {len(misclassified_as_options)} PRIVATE symbols misclassified as OPTIONS:")
            for pos in misclassified_as_options:
                logger.error(f"    - {pos.symbol} (should be PRIVATE, classified as OPTIONS)")

        # Check for option symbols in private category
        misclassified_as_private = []
        for pos in private_classified:
            # Real options have specific format: 6-char base + date + C/P + strike
            is_likely_option = (
                len(pos.symbol) > 15 and
                (pos.symbol[-9] in ['C', 'P'] or pos.symbol[-8] in ['C', 'P']) and
                pos.symbol[6:12].isdigit()  # Has date portion
            )
            if is_likely_option:
                misclassified_as_private.append(pos)

        if misclassified_as_private:
            logger.error(f"⚠️  Found {len(misclassified_as_private)} OPTIONS symbols misclassified as PRIVATE:")
            for pos in misclassified_as_private:
                logger.error(f"    - {pos.symbol} (should be OPTIONS, classified as PRIVATE)")

        if not misclassified_as_options and not misclassified_as_private:
            logger.info("✓ No obvious misclassifications detected!")

        logger.info(f"\n{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(check_position_classifications())
