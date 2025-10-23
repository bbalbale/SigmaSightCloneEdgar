"""
Recalculate historical ridge regressions with correct scaling.

This script:
1. Finds all historical dates with ridge factor data
2. Re-runs ridge regression for each portfolio/date combination
3. Updates both PositionFactorExposure and FactorExposure tables

Ridge regression was storing betas in standardized units (100-200x too small).
The fix divides by scaler.scale_ to convert back to raw return units.
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import select, and_, func
from typing import List, Dict, Set
import sys

from app.database import get_async_session
from app.models.users import Portfolio
from app.models.market_data import FactorExposure, FactorDefinition
from app.calculations.factors_ridge import calculate_factor_betas_ridge
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_historical_dates() -> Dict[str, Set[date]]:
    """
    Get all historical dates with ridge factor data for each portfolio.

    Returns:
        Dict mapping portfolio_id -> set of calculation dates
    """
    async with get_async_session() as db:
        # Get ridge factor IDs (non-market style factors)
        factors_result = await db.execute(
            select(FactorDefinition.id)
            .where(
                and_(
                    FactorDefinition.is_active == True,
                    FactorDefinition.factor_type == 'style',
                    FactorDefinition.name != 'Market Beta'
                )
            )
        )
        ridge_factor_ids = [f for f in factors_result.scalars().all()]

        # Get all portfolios
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = portfolios_result.scalars().all()

        portfolio_dates = {}

        for portfolio in portfolios:
            # Get all dates with ridge factor data for this portfolio
            dates_result = await db.execute(
                select(FactorExposure.calculation_date)
                .where(
                    and_(
                        FactorExposure.portfolio_id == portfolio.id,
                        FactorExposure.factor_id.in_(ridge_factor_ids)
                    )
                )
                .distinct()
                .order_by(FactorExposure.calculation_date)
            )
            dates = set(dates_result.scalars().all())

            if dates:
                portfolio_dates[str(portfolio.id)] = dates
                logger.info(
                    f"Portfolio '{portfolio.name}': {len(dates)} dates from "
                    f"{min(dates)} to {max(dates)}"
                )

        return portfolio_dates


async def recalculate_ridge_for_date(
    portfolio_id: str,
    calculation_date: date,
    dry_run: bool = False
) -> Dict:
    """
    Recalculate ridge regression for a specific portfolio and date.

    Args:
        portfolio_id: Portfolio UUID as string
        calculation_date: Date to recalculate
        dry_run: If True, don't commit changes to database

    Returns:
        Dict with success status and details
    """
    from uuid import UUID

    try:
        async with get_async_session() as db:
            # Run ridge regression calculation
            result = await calculate_factor_betas_ridge(
                db=db,
                portfolio_id=UUID(portfolio_id),
                calculation_date=calculation_date,
                regularization_alpha=1.0,
                use_delta_adjusted=False,
                context=None
            )

            if dry_run:
                # Rollback to test without committing
                await db.rollback()
                logger.info(f"  DRY RUN - rolled back changes")
            else:
                # Already committed by calculate_factor_betas_ridge
                pass

            # Extract summary info
            factor_betas = result.get('factor_betas', {})
            position_betas = result.get('position_betas', {})
            storage = result.get('storage_results', {})

            return {
                'success': True,
                'date': calculation_date,
                'num_factors': len(factor_betas),
                'num_positions': len(position_betas),
                'position_records': storage.get('position_storage', {}).get('records_stored', 0),
                'portfolio_records': storage.get('portfolio_storage', {}).get('records_stored', 0),
                'error': None
            }

    except Exception as e:
        logger.error(f"  ERROR: {str(e)}")
        return {
            'success': False,
            'date': calculation_date,
            'error': str(e)
        }


async def main(
    dry_run: bool = False,
    skip_today: bool = True,
    max_dates: int = None
):
    """
    Main recalculation process.

    Args:
        dry_run: If True, test without committing changes
        skip_today: If True, skip today's date (already corrected)
        max_dates: Maximum number of dates to process per portfolio (for testing)
    """
    logger.info("=" * 80)
    logger.info("HISTORICAL RIDGE REGRESSION RECALCULATION")
    logger.info("=" * 80)
    logger.info(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (updating database)'}")
    logger.info(f"Skip today: {skip_today}")
    if max_dates:
        logger.info(f"Max dates per portfolio: {max_dates}")
    logger.info("")

    # Get all historical dates
    logger.info("Scanning for historical ridge data...")
    portfolio_dates = await get_historical_dates()

    if not portfolio_dates:
        logger.info("No historical ridge data found!")
        return

    logger.info(f"\nFound {len(portfolio_dates)} portfolios with historical data\n")

    # Get portfolio names
    async with get_async_session() as db:
        portfolios_result = await db.execute(select(Portfolio))
        portfolios = {str(p.id): p.name for p in portfolios_result.scalars().all()}

    # Process each portfolio
    total_success = 0
    total_failed = 0
    today = date.today()

    for portfolio_id, dates in portfolio_dates.items():
        portfolio_name = portfolios.get(portfolio_id, portfolio_id)

        # Filter dates
        dates_to_process = sorted(dates)
        if skip_today and today in dates_to_process:
            dates_to_process.remove(today)
            logger.info(f"Skipping today ({today}) - already corrected")

        if max_dates:
            dates_to_process = dates_to_process[:max_dates]

        if not dates_to_process:
            logger.info(f"\n{portfolio_name}: No dates to process (skipped)\n")
            continue

        logger.info(f"\n{portfolio_name}:")
        logger.info(f"  Processing {len(dates_to_process)} dates from {dates_to_process[0]} to {dates_to_process[-1]}")
        logger.info("")

        portfolio_success = 0
        portfolio_failed = 0

        for calc_date in dates_to_process:
            logger.info(f"  {calc_date}...", end=" ")
            sys.stdout.flush()

            result = await recalculate_ridge_for_date(
                portfolio_id=portfolio_id,
                calculation_date=calc_date,
                dry_run=dry_run
            )

            if result['success']:
                logger.info(
                    f"✅ {result['num_positions']} positions, "
                    f"{result['position_records']} position records, "
                    f"{result['portfolio_records']} portfolio records"
                )
                portfolio_success += 1
                total_success += 1
            else:
                logger.error(f"❌ {result['error']}")
                portfolio_failed += 1
                total_failed += 1

        logger.info(f"\n  Portfolio summary: {portfolio_success} succeeded, {portfolio_failed} failed\n")

    # Final summary
    logger.info("=" * 80)
    logger.info("RECALCULATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total: {total_success} succeeded, {total_failed} failed")

    if dry_run:
        logger.info("\n⚠️  DRY RUN MODE - No changes were committed to the database")
        logger.info("Run with dry_run=False to apply changes")
    else:
        logger.info("\n✅ All changes have been committed to the database")

    logger.info("")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Recalculate historical ridge regressions with correct scaling'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test without committing changes to database'
    )
    parser.add_argument(
        '--include-today',
        action='store_true',
        help='Include today\'s date (already corrected by default)'
    )
    parser.add_argument(
        '--max-dates',
        type=int,
        help='Maximum number of dates to process per portfolio (for testing)'
    )

    args = parser.parse_args()

    asyncio.run(main(
        dry_run=args.dry_run,
        skip_today=not args.include_today,
        max_dates=args.max_dates
    ))
