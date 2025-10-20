"""
Backfill Spread Factor Data for 180 Days
Calculates and stores spread factor exposures for historical dates.

This script:
1. Gets all active portfolios (or a specific portfolio if provided)
2. Calculates spread factors for each day in the past 180 days
3. Stores results in factor_exposures tables (position and portfolio level)

Usage:
    # Backfill all portfolios
    python scripts/backfill_spread_factors.py

    # Backfill specific portfolio
    python scripts/backfill_spread_factors.py --portfolio-id <uuid>

    # Backfill specific date range
    python scripts/backfill_spread_factors.py --start-date 2025-04-01 --end-date 2025-10-20

Created: 2025-10-20
"""
import asyncio
from datetime import date, timedelta
from typing import Optional
from uuid import UUID
import argparse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.calculations.factors_spread import calculate_portfolio_spread_betas
from app.core.logging import get_logger
from app.utils.trading_calendar import trading_calendar

logger = get_logger(__name__)


async def backfill_portfolio_spread_factors(
    db: AsyncSession,
    portfolio_id: UUID,
    start_date: date,
    end_date: date
) -> dict:
    """
    Backfill spread factors for a single portfolio across date range.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        start_date: Start date for backfill
        end_date: End date for backfill

    Returns:
        Dict with backfill statistics
    """
    # Get portfolio for logging
    portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        logger.error(f"Portfolio {portfolio_id} not found")
        return {'success': False, 'error': 'Portfolio not found'}

    logger.info(
        f"Starting spread factor backfill for portfolio '{portfolio.name}' "
        f"from {start_date} to {end_date}"
    )

    # Get all trading days in range
    trading_days = []
    current_date = start_date
    while current_date <= end_date:
        if trading_calendar.is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += timedelta(days=1)

    logger.info(f"Found {len(trading_days)} trading days to backfill")

    # Calculate spread factors for each date
    successful = 0
    skipped = 0
    failed = 0
    results = []

    for calc_date in trading_days:
        try:
            logger.info(f"Calculating spread factors for {portfolio.name} on {calc_date}")

            result = await calculate_portfolio_spread_betas(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calc_date,
                context=None  # Let function load its own context
            )

            # Check result status
            metadata = result.get('metadata', {})
            if metadata.get('status') == 'SKIPPED_NO_POSITIONS':
                skipped += 1
                logger.info(f"  Skipped {calc_date}: No positions")
            else:
                successful += 1
                factor_betas = result.get('factor_betas', {})
                logger.info(
                    f"  ✅ {calc_date}: {len(factor_betas)} factors calculated "
                    f"({result.get('data_quality', {}).get('regression_days', 0)} days of data)"
                )

            results.append({
                'date': calc_date,
                'success': True,
                'factor_betas': result.get('factor_betas', {}),
                'status': metadata.get('status', 'COMPLETED')
            })

        except Exception as e:
            failed += 1
            logger.error(f"  ❌ {calc_date}: Failed - {str(e)}")
            results.append({
                'date': calc_date,
                'success': False,
                'error': str(e)
            })

    # Summary
    logger.info(
        f"Backfill complete for {portfolio.name}: "
        f"{successful} successful, {skipped} skipped, {failed} failed "
        f"out of {len(trading_days)} trading days"
    )

    return {
        'success': True,
        'portfolio_id': str(portfolio_id),
        'portfolio_name': portfolio.name,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'trading_days': len(trading_days),
        'successful': successful,
        'skipped': skipped,
        'failed': failed,
        'results': results
    }


async def backfill_all_portfolios(
    start_date: date,
    end_date: date,
    portfolio_id: Optional[str] = None
) -> None:
    """
    Main backfill function - processes all portfolios or a specific one.

    Args:
        start_date: Start date for backfill
        end_date: End date for backfill
        portfolio_id: Optional specific portfolio UUID to backfill
    """
    async with AsyncSessionLocal() as db:
        # Get portfolios to process
        if portfolio_id:
            # Single portfolio
            portfolio_uuid = UUID(portfolio_id)
            stmt = select(Portfolio).where(
                Portfolio.id == portfolio_uuid,
                Portfolio.deleted_at.is_(None)
            )
        else:
            # All active portfolios
            stmt = select(Portfolio).where(Portfolio.deleted_at.is_(None))

        result = await db.execute(stmt)
        portfolios = result.scalars().all()

        if not portfolios:
            logger.warning("No portfolios found to backfill")
            return

        logger.info(f"Starting spread factor backfill for {len(portfolios)} portfolios")
        logger.info(f"Date range: {start_date} to {end_date}")

        # Process each portfolio
        all_results = []
        for i, portfolio in enumerate(portfolios, 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing portfolio {i}/{len(portfolios)}: {portfolio.name}")
            logger.info(f"{'='*70}")

            portfolio_result = await backfill_portfolio_spread_factors(
                db=db,
                portfolio_id=portfolio.id,
                start_date=start_date,
                end_date=end_date
            )

            all_results.append(portfolio_result)

        # Final summary
        logger.info(f"\n{'='*70}")
        logger.info("BACKFILL SUMMARY")
        logger.info(f"{'='*70}")

        total_successful = sum(r['successful'] for r in all_results)
        total_skipped = sum(r['skipped'] for r in all_results)
        total_failed = sum(r['failed'] for r in all_results)
        total_trading_days = sum(r['trading_days'] for r in all_results)

        logger.info(f"Portfolios processed: {len(all_results)}")
        logger.info(f"Total trading days: {total_trading_days}")
        logger.info(f"Successful calculations: {total_successful}")
        logger.info(f"Skipped (no positions): {total_skipped}")
        logger.info(f"Failed: {total_failed}")
        logger.info(f"{'='*70}\n")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Backfill spread factor data for portfolios"
    )
    parser.add_argument(
        '--portfolio-id',
        type=str,
        help='Specific portfolio UUID to backfill (optional)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD). Default: 180 days ago'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD). Default: today'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=180,
        help='Number of days to backfill (default: 180)'
    )

    args = parser.parse_args()

    # Parse dates
    if args.end_date:
        end_date = date.fromisoformat(args.end_date)
    else:
        end_date = date.today()

    if args.start_date:
        start_date = date.fromisoformat(args.start_date)
    else:
        start_date = end_date - timedelta(days=args.days)

    # Run backfill
    logger.info("=" * 70)
    logger.info("SPREAD FACTOR BACKFILL SCRIPT")
    logger.info("=" * 70)
    logger.info(f"Start date: {start_date}")
    logger.info(f"End date: {end_date}")
    logger.info(f"Portfolio: {args.portfolio_id or 'ALL'}")
    logger.info("=" * 70 + "\n")

    asyncio.run(backfill_all_portfolios(
        start_date=start_date,
        end_date=end_date,
        portfolio_id=args.portfolio_id
    ))


if __name__ == "__main__":
    main()
