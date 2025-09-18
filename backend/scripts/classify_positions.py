#!/usr/bin/env python
"""
Script to classify existing positions with investment_class and investment_subtype.
This implements the classification logic from the implementation plan.
"""
import asyncio
from uuid import UUID
from typing import Tuple, Optional
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger(__name__)


def classify_position(position: Position) -> Tuple[str, str]:
    """
    Classify a position based on its position_type.
    Returns (investment_class, investment_subtype) tuple.
    """
    # Options are clearly identified by position_type
    if position.position_type in [PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP]:
        return 'OPTIONS', 'LISTED_OPTION'

    # Check for private investments (for now, none in demo data)
    # In the future, this could check against a list of known private investment symbols
    if is_private_investment_symbol(position.symbol):
        return 'PRIVATE', determine_private_subtype(position.symbol)

    # Default to public equity
    return 'PUBLIC', 'STOCK'


def is_private_investment_symbol(symbol: str) -> bool:
    """
    Check if a symbol represents a private investment.
    For demo data, we don't have any private investments.
    """
    # List of known private investment patterns
    private_patterns = [
        'PRIVATE_',
        'FUND_',
        'PE_',
        'VC_',
        'HF_'
    ]

    return any(symbol.upper().startswith(pattern) for pattern in private_patterns)


def determine_private_subtype(symbol: str) -> str:
    """
    Determine the subtype for a private investment.
    """
    symbol_upper = symbol.upper()

    if 'PE_' in symbol_upper:
        return 'PE_FUND'
    elif 'VC_' in symbol_upper:
        return 'VC_FUND'
    elif 'HF_' in symbol_upper or 'HEDGE' in symbol_upper:
        return 'HEDGE_FUND'
    elif 'FUND_' in symbol_upper:
        return 'FUND'
    else:
        return 'PRIVATE_OTHER'


async def classify_all_positions():
    """
    Classify all existing positions in the database.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get all positions that haven't been classified
            result = await db.execute(
                select(Position).where(Position.investment_class.is_(None))
            )
            positions = result.scalars().all()

            if not positions:
                logger.info("No unclassified positions found")
                return

            logger.info(f"Found {len(positions)} unclassified positions")

            # Statistics
            stats = {
                'PUBLIC': 0,
                'OPTIONS': 0,
                'PRIVATE': 0
            }

            # Classify each position
            for position in positions:
                investment_class, investment_subtype = classify_position(position)

                # Update the position
                position.investment_class = investment_class
                position.investment_subtype = investment_subtype

                stats[investment_class] += 1

                logger.debug(f"Classified {position.symbol} ({position.position_type.value}) as {investment_class}/{investment_subtype}")

            # Commit all changes
            await db.commit()

            # Report statistics
            logger.info("Classification complete:")
            logger.info(f"  PUBLIC: {stats['PUBLIC']} positions")
            logger.info(f"  OPTIONS: {stats['OPTIONS']} positions")
            logger.info(f"  PRIVATE: {stats['PRIVATE']} positions")

        except Exception as e:
            logger.error(f"Error classifying positions: {e}")
            await db.rollback()
            raise


async def verify_classification():
    """
    Verify that all positions have been classified correctly.
    """
    async with AsyncSessionLocal() as db:
        # Check for any unclassified positions
        result = await db.execute(
            select(Position).where(Position.investment_class.is_(None))
        )
        unclassified = result.scalars().all()

        if unclassified:
            logger.warning(f"Found {len(unclassified)} unclassified positions:")
            for pos in unclassified:
                logger.warning(f"  - {pos.symbol} ({pos.position_type.value})")
        else:
            logger.info("✅ All positions have been classified")

        # Show classification summary
        result = await db.execute(
            select(Position)
        )
        all_positions = result.scalars().all()

        summary = {}
        for pos in all_positions:
            key = f"{pos.investment_class or 'UNCLASSIFIED'}/{pos.investment_subtype or 'NONE'}"
            summary[key] = summary.get(key, 0) + 1

        logger.info("\nClassification Summary:")
        for key, count in sorted(summary.items()):
            logger.info(f"  {key}: {count} positions")


async def main():
    """
    Main function to run the classification script.
    """
    logger.info("Starting position classification...")

    # Classify all positions
    await classify_all_positions()

    # Verify the classification
    await verify_classification()

    logger.info("Classification script complete")


if __name__ == "__main__":
    asyncio.run(main())