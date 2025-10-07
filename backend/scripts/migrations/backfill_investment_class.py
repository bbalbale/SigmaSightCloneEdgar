"""
Backfill investment_class for existing positions

Phase 8.1 Task 11a: One-time backfill script for Railway database

This script:
1. Identifies positions with NULL investment_class
2. Applies the determine_investment_class() heuristic
3. Updates investment_class and investment_subtype fields
4. Reports results with position counts and classifications

Usage:
    # Dry run (no changes)
    uv run python scripts/migrations/backfill_investment_class.py --dry-run

    # Apply changes
    uv run python scripts/migrations/backfill_investment_class.py --apply

    # Target specific portfolio
    uv run python scripts/migrations/backfill_investment_class.py --portfolio-id <uuid> --apply
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.positions import Position
from app.core.logging import get_logger

logger = get_logger(__name__)


def determine_investment_class(symbol: str) -> str:
    """
    Determine investment class from symbol (same logic as seed_demo_portfolios.py)

    Returns:
        'OPTIONS' for options (symbols with expiry/strike pattern)
        'PRIVATE' for private investment funds
        'PUBLIC' for regular stocks and ETFs
    """
    # Check if it's an option (has expiry date and strike price pattern)
    if len(symbol) > 10 and any(char in symbol for char in ['C', 'P']):
        return 'OPTIONS'

    # Check for private investment patterns (Phase 8.1 enhanced heuristic)
    private_patterns = [
        'PRIVATE', 'FUND', '_VC_', '_PE_', 'REIT', 'SIGMA',  # Original
        'HOME_', 'RENTAL_', 'ART_', 'CRYPTO_', 'TREASURY', 'MONEY_MARKET'  # Phase 8.1
    ]
    if any(pattern in symbol.upper() for pattern in private_patterns):
        return 'PRIVATE'

    # Everything else is public equity (stocks, ETFs, mutual funds)
    return 'PUBLIC'


def determine_investment_subtype(symbol: str) -> str:
    """
    Determine investment subtype for PRIVATE positions
    """
    symbol_upper = symbol.upper()

    # Private equity patterns
    if any(pattern in symbol_upper for pattern in ['_PE_', 'PRIVATE_EQUITY', 'BX_', 'KKR_']):
        return 'PRIVATE_EQUITY'

    # Venture capital patterns
    if any(pattern in symbol_upper for pattern in ['_VC_', 'VENTURE', 'A16Z_', 'SEQUOIA_']):
        return 'VENTURE_CAPITAL'

    # Private REIT patterns
    if 'REIT' in symbol_upper and any(pattern in symbol_upper for pattern in ['PRIVATE', 'STARWOOD']):
        return 'PRIVATE_REIT'

    # Hedge fund patterns
    if 'FUND' in symbol_upper and any(pattern in symbol_upper for pattern in ['SIGMA', 'CITADEL', 'RENAISSANCE']):
        return 'HEDGE_FUND'

    # Real estate patterns
    if any(pattern in symbol_upper for pattern in ['HOME_', 'RENTAL_', 'RE_', 'PROPERTY']):
        return 'PRIVATE_REAL_ESTATE'

    # Alternative assets
    if any(pattern in symbol_upper for pattern in ['CRYPTO_', 'ART_', 'TREASURY', 'MONEY_MARKET', 'COLLECTIBLE']):
        return 'OTHER_ALTERNATIVE'

    # Default for PRIVATE without specific subtype
    return 'OTHER_PRIVATE'


async def backfill_investment_class(
    db: AsyncSession,
    portfolio_id: UUID = None,
    dry_run: bool = True
) -> Dict:
    """
    Backfill investment_class for positions with NULL values

    Args:
        db: Database session
        portfolio_id: Optional portfolio UUID to limit scope
        dry_run: If True, report changes without applying them

    Returns:
        Dictionary with statistics
    """
    # Count total positions with NULL investment_class
    count_stmt = select(func.count(Position.id)).where(
        Position.investment_class.is_(None)
    )
    if portfolio_id:
        count_stmt = count_stmt.where(Position.portfolio_id == portfolio_id)

    result = await db.execute(count_stmt)
    total_null = result.scalar() or 0

    logger.info(f"Found {total_null} positions with NULL investment_class")

    if total_null == 0:
        return {
            'total_positions_checked': 0,
            'positions_updated': 0,
            'classifications': {},
            'dry_run': dry_run
        }

    # Fetch positions with NULL investment_class
    stmt = select(Position).where(Position.investment_class.is_(None))
    if portfolio_id:
        stmt = stmt.where(Position.portfolio_id == portfolio_id)

    result = await db.execute(stmt)
    positions = result.scalars().all()

    # Track statistics
    classifications = {'PUBLIC': 0, 'PRIVATE': 0, 'OPTIONS': 0}
    subtypes = {}
    updates = []

    for position in positions:
        # Determine classification
        investment_class = determine_investment_class(position.symbol)
        classifications[investment_class] += 1

        # Determine subtype for PRIVATE positions
        investment_subtype = None
        if investment_class == 'PRIVATE':
            investment_subtype = determine_investment_subtype(position.symbol)
            subtypes[investment_subtype] = subtypes.get(investment_subtype, 0) + 1

        updates.append({
            'position_id': position.id,
            'symbol': position.symbol,
            'old_class': position.investment_class,
            'new_class': investment_class,
            'new_subtype': investment_subtype
        })

        if not dry_run:
            position.investment_class = investment_class
            position.investment_subtype = investment_subtype

    # Commit changes if not dry run
    if not dry_run:
        await db.commit()
        logger.info(f"Updated {len(updates)} positions")
    else:
        logger.info(f"Dry run: Would update {len(updates)} positions")
        await db.rollback()

    # Log sample updates
    logger.info("\n=== Classification Summary ===")
    logger.info(f"PUBLIC: {classifications['PUBLIC']}")
    logger.info(f"PRIVATE: {classifications['PRIVATE']}")
    logger.info(f"OPTIONS: {classifications['OPTIONS']}")

    if subtypes:
        logger.info("\n=== Private Investment Subtypes ===")
        for subtype, count in sorted(subtypes.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"{subtype}: {count}")

    # Show first 10 updates as examples
    logger.info("\n=== Sample Updates (first 10) ===")
    for update in updates[:10]:
        logger.info(
            f"{update['symbol']:30} -> {update['new_class']:10} "
            f"(subtype: {update['new_subtype'] or 'N/A'})"
        )

    return {
        'total_positions_checked': total_null,
        'positions_updated': len(updates) if not dry_run else 0,
        'classifications': classifications,
        'subtypes': subtypes,
        'dry_run': dry_run,
        'sample_updates': updates[:10]
    }


async def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Backfill investment_class for positions')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--apply', action='store_true', help='Apply changes to database')
    parser.add_argument('--portfolio-id', type=str, help='Target specific portfolio UUID')

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        logger.error("Must specify either --dry-run or --apply")
        return

    dry_run = args.dry_run
    portfolio_id = UUID(args.portfolio_id) if args.portfolio_id else None

    logger.info("=" * 80)
    logger.info("Investment Class Backfill Script")
    logger.info("=" * 80)
    logger.info(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLY (will update database)'}")
    if portfolio_id:
        logger.info(f"Scope: Portfolio {portfolio_id}")
    else:
        logger.info("Scope: All portfolios")
    logger.info("=" * 80)

    async with get_async_session() as db:
        results = await backfill_investment_class(db, portfolio_id, dry_run)

    logger.info("\n" + "=" * 80)
    logger.info("Backfill Complete")
    logger.info("=" * 80)
    logger.info(f"Positions checked: {results['total_positions_checked']}")
    logger.info(f"Positions updated: {results['positions_updated']}")
    logger.info(f"Mode: {'DRY RUN' if results['dry_run'] else 'APPLIED'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
