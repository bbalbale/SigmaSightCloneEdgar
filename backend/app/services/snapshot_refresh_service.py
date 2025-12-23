"""
Service for automatically triggering portfolio snapshot recalculations when stale data is detected.
Implements rate-limiting to prevent excessive recalculation requests.

Updated 2025-12-22: Uses symbol-level factor calculation (no position-level fallback).
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.snapshot_helpers import get_snapshot_data_quality
from app.calculations.snapshots import create_portfolio_snapshot
from app.calculations.market_beta import calculate_portfolio_market_beta, calculate_portfolio_provider_beta

logger = get_logger(__name__)

# Rate limiting: Track last recalculation trigger per portfolio
_last_trigger_times: Dict[UUID, datetime] = {}
RECALCULATION_RATE_LIMIT_HOURS = 1


def _should_trigger_recalculation(portfolio_id: UUID) -> bool:
    """
    Check if enough time has passed since last trigger to avoid excessive recalculations.

    Args:
        portfolio_id: Portfolio to check

    Returns:
        True if recalculation should be triggered, False if rate-limited
    """
    now = datetime.utcnow()
    last_trigger = _last_trigger_times.get(portfolio_id)

    if last_trigger is None:
        return True

    time_since_last = now - last_trigger
    hours_since_last = time_since_last.total_seconds() / 3600

    if hours_since_last < RECALCULATION_RATE_LIMIT_HOURS:
        logger.info(
            f"Recalculation for portfolio {portfolio_id} rate-limited: "
            f"only {hours_since_last:.1f} hours since last trigger "
            f"(minimum {RECALCULATION_RATE_LIMIT_HOURS} hours)"
        )
        return False

    return True


def _mark_trigger_time(portfolio_id: UUID):
    """Record that a recalculation was triggered for rate-limiting purposes."""
    _last_trigger_times[portfolio_id] = datetime.utcnow()


async def trigger_portfolio_recalculation(
    db: AsyncSession,
    portfolio_id: UUID,
    force: bool = False
) -> Dict:
    """
    Trigger background recalculation of portfolio snapshot and factor exposures.

    This function is called when stale data is detected. It queues up the necessary
    calculations to bring the portfolio data up to date.

    Args:
        db: Database session
        portfolio_id: Portfolio to recalculate
        force: If True, bypass rate limiting

    Returns:
        Dictionary with trigger status:
        - triggered: Whether recalculation was triggered
        - reason: Why it was or wasn't triggered
        - portfolio_id: Portfolio ID
        - timestamp: When trigger occurred
    """
    # Check rate limiting
    if not force and not _should_trigger_recalculation(portfolio_id):
        return {
            'triggered': False,
            'reason': 'rate_limited',
            'portfolio_id': str(portfolio_id),
            'timestamp': datetime.utcnow().isoformat()
        }

    try:
        logger.info(f"Triggering recalculation for portfolio {portfolio_id}")

        # Mark trigger time for rate limiting
        _mark_trigger_time(portfolio_id)

        # Launch recalculation in background (fire and forget)
        asyncio.create_task(_execute_recalculation(db, portfolio_id))

        return {
            'triggered': True,
            'reason': 'stale_data_detected',
            'portfolio_id': str(portfolio_id),
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error triggering recalculation for portfolio {portfolio_id}: {e}")
        return {
            'triggered': False,
            'reason': f'error: {str(e)}',
            'portfolio_id': str(portfolio_id),
            'timestamp': datetime.utcnow().isoformat()
        }


async def _execute_recalculation(db: AsyncSession, portfolio_id: UUID):
    """
    Execute the actual recalculation (runs in background).

    Performs:
    1. Ridge factor calculation
    2. Market beta calculations
    3. Portfolio snapshot creation

    Args:
        db: Database session (not used - we create independent session)
        portfolio_id: Portfolio to recalculate
    """
    from datetime import date
    from app.database import get_async_session

    calculation_date = date.today()

    # CRITICAL FIX: Create NEW independent session for background operations
    # This prevents "another operation is in progress" errors when batch
    # processing or other API operations are running simultaneously
    async with get_async_session() as independent_db:
        try:
            logger.info(f"Starting background recalculation for portfolio {portfolio_id} (independent session)")

            # 1. Calculate factors using symbol-level approach
            # First ensure symbols have factor betas, then aggregate to portfolio
            logger.info(f"Calculating factors for portfolio {portfolio_id} via symbol aggregation")

            from app.services.portfolio_factor_service import (
                get_portfolio_factor_exposures,
                store_portfolio_factor_exposures
            )
            from app.calculations.symbol_factors import (
                get_uncached_symbols,
                calculate_symbol_ridge_factors,
                calculate_symbol_spread_factors,
                ensure_symbols_in_universe
            )
            from app.models.positions import Position
            from sqlalchemy import select, distinct

            # Get portfolio symbols
            symbol_stmt = select(distinct(Position.symbol)).where(
                Position.portfolio_id == portfolio_id,
                Position.symbol.isnot(None)
            )
            symbol_result = await independent_db.execute(symbol_stmt)
            portfolio_symbols = [row[0] for row in symbol_result.fetchall()]

            # Check which symbols need factor calculation
            uncached = await get_uncached_symbols(
                independent_db, portfolio_symbols, calculation_date, 'ridge_regression'
            )

            if uncached:
                logger.info(f"Calculating factors for {len(uncached)} uncached symbols")
                # Ensure symbols are in universe
                await ensure_symbols_in_universe(independent_db, uncached)

                # Calculate factors for uncached symbols
                for symbol in uncached:
                    try:
                        await calculate_symbol_ridge_factors(
                            independent_db, symbol, calculation_date
                        )
                        await calculate_symbol_spread_factors(
                            independent_db, symbol, calculation_date
                        )
                    except Exception as e:
                        logger.warning(f"Failed to calculate factors for {symbol}: {e}")

                await independent_db.commit()

            # Now aggregate from symbol betas to portfolio
            factor_result = await get_portfolio_factor_exposures(
                db=independent_db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                include_ridge=True,
                include_spread=True
            )

            ridge_betas = factor_result.get('ridge_betas', {})
            spread_betas = factor_result.get('spread_betas', {})

            if ridge_betas or spread_betas:
                await store_portfolio_factor_exposures(
                    db=independent_db,
                    portfolio_id=portfolio_id,
                    calculation_date=calculation_date,
                    ridge_betas=ridge_betas,
                    spread_betas=spread_betas
                )
                await independent_db.commit()
                logger.info(
                    f"Factors calculated for portfolio {portfolio_id}: "
                    f"{len(ridge_betas)} ridge, {len(spread_betas)} spread factors"
                )
            else:
                logger.warning(f"No factors calculated for portfolio {portfolio_id}")

            # 2. Calculate 90-day market beta
            logger.info(f"Calculating 90-day market beta for portfolio {portfolio_id}")
            beta_90d_result = await calculate_portfolio_market_beta(
                db=independent_db,  # Use independent session
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                window_days=90
            )

            # 3. Calculate 1-year provider beta
            logger.info(f"Calculating 1-year provider beta for portfolio {portfolio_id}")
            beta_1y_result = await calculate_portfolio_provider_beta(
                db=independent_db,  # Use independent session
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            # 4. Create/update portfolio snapshot
            logger.info(f"Creating portfolio snapshot for portfolio {portfolio_id}")
            snapshot_result = await create_portfolio_snapshot(
                db=independent_db,  # Use independent session
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )

            if snapshot_result.get('success'):
                logger.info(
                    f"Portfolio snapshot created for portfolio {portfolio_id}: "
                    f"Beta 90d={snapshot_result.get('beta_calculated_90d')}, "
                    f"Beta 1y={snapshot_result.get('beta_provider_1y')}"
                )
            else:
                logger.warning(
                    f"Portfolio snapshot creation failed for portfolio {portfolio_id}: "
                    f"{snapshot_result.get('error')}"
                )

            logger.info(f"Background recalculation completed for portfolio {portfolio_id}")

        except Exception as e:
            logger.error(
                f"Error during background recalculation for portfolio {portfolio_id}: {e}",
                exc_info=True
            )


async def check_and_trigger_refresh_if_needed(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict:
    """
    Check if portfolio data is stale and trigger recalculation if needed.

    This is the main entry point that should be called from services and endpoints
    when they retrieve portfolio data.

    Args:
        db: Database session
        portfolio_id: Portfolio to check

    Returns:
        Dictionary with check results:
        - data_quality: Quality assessment
        - trigger_result: Result of trigger attempt (if triggered)
    """
    # Get data quality assessment
    quality = await get_snapshot_data_quality(db, portfolio_id)

    # Check if recalculation should be triggered
    if quality['should_recalculate']:
        trigger_result = await trigger_portfolio_recalculation(db, portfolio_id)
        return {
            'data_quality': quality,
            'trigger_result': trigger_result
        }
    else:
        return {
            'data_quality': quality,
            'trigger_result': {
                'triggered': False,
                'reason': 'data_is_current',
                'portfolio_id': str(portfolio_id)
            }
        }
