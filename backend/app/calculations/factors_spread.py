"""
Spread Factor Analysis - Long-Short Factor Betas
Calculates portfolio exposure to 4 long-short spread factors using 180-day OLS regression.

Addresses multicollinearity by using factor spreads instead of raw factor ETFs:
- Growth-Value Spread (VUG - VTV): ~0.3 correlation with market (vs 0.93+ for raw)
- Momentum Spread (MTUM - SPY): Independent momentum exposure
- Size Spread (IWM - SPY): Small vs large cap tilt
- Quality Spread (QUAL - SPY): Quality vs market exposure

Created: 2025-10-20
Architecture: Position-First (November 2025 Refactoring)
Regression Window: 180 days (6 months)

================================================================================
ARCHITECTURE: Position-First with Caching
================================================================================
This module follows the position-first calculation pattern (same as market_beta.py):
  1. Check cache: which positions already have 4 spread factors for this date?
  2. Calculate OLS regression ONLY for uncached positions
  3. Persist position-level results immediately
  4. Load cached + newly calculated betas for portfolio aggregation
  5. Store portfolio-level aggregates

This avoids recalculating betas for positions shared across multiple portfolios.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.positions import Position
from app.models.market_data import FactorDefinition
from app.constants.factors import (
    SPREAD_FACTORS, SPREAD_REGRESSION_WINDOW_DAYS,
    SPREAD_MIN_REGRESSION_DAYS, BETA_CAP_LIMIT
)
from app.calculations.factor_utils import (
    PortfolioContext, load_portfolio_context,
    get_default_data_quality,
    get_default_storage_results,
    bulk_load_cached_position_factors,
    persist_position_factor_betas,
    aggregate_position_betas_to_portfolio,
    calculate_position_weights,
)
from app.calculations.market_data import get_position_value, get_returns
from app.calculations.regression_utils import run_single_factor_regression
from app.core.logging import get_logger

logger = get_logger(__name__)

EXPECTED_SPREAD_FACTOR_COUNT = 4


async def fetch_spread_returns(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    price_cache=None
) -> pd.DataFrame:
    """
    Calculate daily returns for 4 spread factors using canonical get_returns().

    Spread Return = Long ETF Return - Short ETF Return

    This creates factors that are less correlated with the market, eliminating
    the multicollinearity problem in traditional multi-factor models.

    Args:
        db: Database session
        start_date: Start date for data fetch
        end_date: End date for data fetch
        price_cache: Optional PriceCache for optimized price lookups

    Returns:
        DataFrame with 4 columns (spread factor names) and date index.
    """
    logger.info(f"Fetching spread returns from {start_date} to {end_date}")

    # Collect all unique ETF symbols needed
    etf_symbols = set()
    for long_etf, short_etf in SPREAD_FACTORS.values():
        etf_symbols.add(long_etf)
        etf_symbols.add(short_etf)

    # Use canonical get_returns() function
    returns = await get_returns(
        db=db,
        symbols=list(etf_symbols),
        start_date=start_date,
        end_date=end_date,
        align_dates=True,
        price_cache=price_cache
    )

    if returns.empty:
        raise ValueError("No price data available for spread factors")

    # Calculate spread returns
    spread_returns = pd.DataFrame(index=returns.index)

    for spread_name, (long_etf, short_etf) in SPREAD_FACTORS.items():
        if long_etf in returns.columns and short_etf in returns.columns:
            spread_returns[spread_name] = returns[long_etf] - returns[short_etf]
        else:
            logger.warning(f"Missing data for {spread_name}: {long_etf} or {short_etf}")
            spread_returns[spread_name] = np.nan

    # Drop rows with any NaN values
    spread_returns = spread_returns.dropna()

    logger.info(f"Calculated spread returns for {len(spread_returns)} days")
    return spread_returns


async def calculate_single_position_spread_betas(
    position_returns: pd.Series,
    spread_returns: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate spread factor betas for a single position using OLS regression.

    Runs 4 separate univariate OLS regressions:
        position_return = alpha + beta * spread_return + error

    Args:
        position_returns: Daily returns for the position (pd.Series with date index)
        spread_returns: Daily returns for 4 spread factors (pd.DataFrame with date index)

    Returns:
        Dictionary containing:
        - betas: Dict mapping spread factor names to beta values
        - r_squared: Average R² across all factors
        - observations: Number of data points used
        - success: Whether at least one regression succeeded
        - errors: List of errors if any
    """
    # Align position and spread returns on common dates
    data = pd.concat([position_returns, spread_returns], axis=1).dropna()

    if len(data) < SPREAD_MIN_REGRESSION_DAYS:
        return {
            'betas': {},
            'r_squared': 0.0,
            'observations': len(data),
            'success': False,
            'error': f'Insufficient data: {len(data)} days (minimum: {SPREAD_MIN_REGRESSION_DAYS})'
        }

    y = data.iloc[:, 0].values  # Position returns
    factor_betas = {}
    total_r_squared = 0.0
    successful_count = 0
    errors = []

    for spread_name in spread_returns.columns:
        if spread_name not in data.columns:
            continue

        x = data[spread_name].values

        try:
            result = run_single_factor_regression(
                y=y,
                x=x,
                cap=BETA_CAP_LIMIT,
                confidence=0.10,
                return_diagnostics=True
            )

            factor_betas[spread_name] = result['beta']
            total_r_squared += result['r_squared']
            successful_count += 1

        except Exception as e:
            errors.append(f"{spread_name}: {str(e)}")
            logger.debug(f"OLS regression failed for {spread_name}: {e}")

    if successful_count == 0:
        return {
            'betas': {},
            'r_squared': 0.0,
            'observations': len(data),
            'success': False,
            'error': f'All regressions failed: {errors}'
        }

    return {
        'betas': factor_betas,
        'r_squared': total_r_squared / successful_count,
        'observations': len(data),
        'success': True,
        'error': None,
        'errors': errors if errors else None
    }


async def calculate_portfolio_spread_betas(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    context: Optional[PortfolioContext] = None,
    price_cache=None
) -> Dict[str, Any]:
    """
    Calculate portfolio-level spread factor betas using 180-day OLS regression.

    ARCHITECTURE: Position-First with Caching
    =========================================
    1. Load portfolio context (positions, equity, factor definitions)
    2. Check cache: which positions already have 4 spread factors for this date?
    3. Fetch spread returns (VUG-VTV, MTUM-SPY, IWM-SPY, QUAL-SPY)
    4. Fetch position returns for uncached positions only
    5. Run 4 OLS regressions for each uncached position
    6. Persist position-level betas immediately
    7. Load all position betas (cached + newly calculated)
    8. Aggregate to portfolio level
    9. Store portfolio-level factor exposures

    This pattern matches market_beta.py, interest_rate_beta.py, and factors_ridge.py.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Calculation date (end of regression window)
        context: Pre-loaded portfolio context (optional)
        price_cache: Optional PriceCache for optimized price lookups

    Returns:
        Dictionary containing factor betas, position betas, diagnostics, etc.
    """
    logger.info(
        f"Calculating spread factor betas for portfolio {portfolio_id} "
        f"as of {calculation_date} (180-day window)"
    )

    # Step 1: Load context if not provided
    if context is None:
        logger.info("Loading portfolio context")
        context = await load_portfolio_context(db, portfolio_id, calculation_date)

    # Get public positions only (spread factors don't apply to PRIVATE)
    public_positions = [
        p for p in context.public_positions
        if p.investment_class == 'PUBLIC' and p.position_type in ('LONG', 'SHORT')
    ]

    if not public_positions:
        counts = context.get_position_count_summary()
        logger.info(
            f"No PUBLIC equity positions for portfolio {portfolio_id} - skipping spread factors. "
            f"Position counts: {counts}"
        )
        return _build_skip_result(portfolio_id, calculation_date, context, 'no_public_positions')

    position_ids = [p.id for p in public_positions]
    logger.info(f"Found {len(position_ids)} PUBLIC equity positions for spread calculation")

    # Step 2: Check cache - which positions already have 4 spread factors?
    cached_betas = await bulk_load_cached_position_factors(
        db=db,
        position_ids=position_ids,
        factor_type='spread',
        calculation_date=calculation_date,
        expected_factor_count=EXPECTED_SPREAD_FACTOR_COUNT
    )

    positions_needing_calculation = [
        p for p in public_positions
        if p.id not in cached_betas
    ]

    logger.info(
        f"Cache check: {len(cached_betas)} positions cached, "
        f"{len(positions_needing_calculation)} need calculation"
    )

    # Step 3: Fetch spread returns
    end_date = calculation_date
    start_date = end_date - timedelta(days=SPREAD_REGRESSION_WINDOW_DAYS + 30)

    try:
        spread_returns = await fetch_spread_returns(db, start_date, end_date, price_cache)
    except ValueError as e:
        logger.error(f"Failed to fetch spread returns: {e}")
        return _build_skip_result(portfolio_id, calculation_date, context, 'no_spread_data')

    logger.info(f"Spread returns: {len(spread_returns)} days, factors: {list(spread_returns.columns)}")

    # Step 4 & 5: Calculate spread betas for uncached positions
    newly_calculated_betas = {}
    spread_diagnostics = {
        'positions_from_cache': len(cached_betas),
        'positions_calculated': 0,
        'positions_failed': 0,
        'avg_r_squared': 0.0,
    }

    if positions_needing_calculation:
        # Fetch position returns for uncached positions
        uncached_symbols = list(set(p.symbol for p in positions_needing_calculation))

        position_returns_df = await get_returns(
            db=db,
            symbols=uncached_symbols,
            start_date=start_date,
            end_date=end_date,
            align_dates=True,
            price_cache=price_cache
        )

        if position_returns_df.empty:
            logger.warning("No position returns available for uncached positions")
        else:
            # Align spread and position returns
            common_dates = spread_returns.index.intersection(position_returns_df.index)
            spread_returns_aligned = spread_returns.loc[common_dates]

            total_r_squared = 0.0

            for position in positions_needing_calculation:
                if position.symbol not in position_returns_df.columns:
                    logger.debug(f"No return data for {position.symbol}")
                    spread_diagnostics['positions_failed'] += 1
                    continue

                pos_returns = position_returns_df[position.symbol].loc[common_dates]

                # Run OLS regressions
                result = await calculate_single_position_spread_betas(
                    position_returns=pos_returns,
                    spread_returns=spread_returns_aligned
                )

                if result['success'] and result['betas']:
                    newly_calculated_betas[position.id] = result['betas']
                    spread_diagnostics['positions_calculated'] += 1
                    total_r_squared += result['r_squared']

                    # Step 6: Persist immediately
                    await persist_position_factor_betas(
                        db=db,
                        position_id=position.id,
                        factor_betas=result['betas'],
                        calculation_date=calculation_date,
                        factor_name_to_id=context.factor_name_to_id,
                        quality_flag='full_history'
                    )
                else:
                    logger.debug(f"Spread calculation failed for {position.symbol}: {result.get('error')}")
                    spread_diagnostics['positions_failed'] += 1

            if spread_diagnostics['positions_calculated'] > 0:
                spread_diagnostics['avg_r_squared'] = total_r_squared / spread_diagnostics['positions_calculated']

    logger.info(
        f"Spread calculation complete: {spread_diagnostics['positions_calculated']} calculated, "
        f"{spread_diagnostics['positions_from_cache']} from cache, "
        f"{spread_diagnostics['positions_failed']} failed"
    )

    # Step 7: Combine cached + newly calculated betas
    all_position_betas = {**cached_betas, **newly_calculated_betas}

    if not all_position_betas:
        logger.warning("No position betas available (all failed or no data)")
        return _build_skip_result(portfolio_id, calculation_date, context, 'no_position_betas')

    # Step 8: Aggregate to portfolio level
    position_weights = calculate_position_weights(
        positions=[p for p in public_positions if p.id in all_position_betas],
        portfolio_equity=float(context.equity_balance)
    )

    portfolio_betas = await aggregate_position_betas_to_portfolio(
        position_betas=all_position_betas,
        position_weights=position_weights
    )

    logger.info(f"Portfolio spread betas: {portfolio_betas}")

    # Step 9: Store portfolio-level factor exposures
    portfolio_storage = await _store_portfolio_spread_exposures(
        db=db,
        portfolio_id=portfolio_id,
        portfolio_betas=portfolio_betas,
        calculation_date=calculation_date,
        context=context
    )

    # Build results
    position_betas_serializable = {
        str(pid): betas for pid, betas in all_position_betas.items()
    }

    results = {
        'success': True,
        'factor_betas': portfolio_betas,
        'position_betas': position_betas_serializable,
        'data_quality': {
            'regression_days': len(spread_returns),
            'required_days': SPREAD_MIN_REGRESSION_DAYS,
            'positions_processed': len(all_position_betas),
            'positions_from_cache': spread_diagnostics['positions_from_cache'],
            'positions_calculated': spread_diagnostics['positions_calculated'],
            'factors_processed': EXPECTED_SPREAD_FACTOR_COUNT
        },
        'metadata': {
            'calculation_date': calculation_date.isoformat(),
            'portfolio_id': str(portfolio_id),
            'method': 'OLS_SPREAD',
            'regression_window_days': SPREAD_REGRESSION_WINDOW_DAYS
        },
        'storage_results': {
            'position_storage': {
                'records_stored': spread_diagnostics['positions_calculated'] * EXPECTED_SPREAD_FACTOR_COUNT,
                'positions_from_cache': spread_diagnostics['positions_from_cache']
            },
            'portfolio_storage': portfolio_storage
        },
        'spread_diagnostics': spread_diagnostics
    }

    logger.info(
        f"[OK] Spread factor calculation complete: "
        f"{len(all_position_betas)} positions, {len(portfolio_betas)} portfolio factors"
    )

    return results


async def _store_portfolio_spread_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    portfolio_betas: Dict[str, float],
    calculation_date: date,
    context: PortfolioContext
) -> Dict[str, Any]:
    """
    Store portfolio-level spread factor exposures to FactorExposure table.

    Uses upsert pattern (update if exists, insert if not).
    """
    from app.models.market_data import FactorExposure
    import uuid

    results = {
        'records_stored': 0,
        'factors_stored': [],
        'errors': []
    }

    portfolio_equity = float(context.equity_balance)

    for factor_name, beta_value in portfolio_betas.items():
        if factor_name not in context.factor_name_to_id:
            results['errors'].append(f"Factor '{factor_name}' not found in database")
            continue

        factor_id = context.factor_name_to_id[factor_name]
        exposure_dollar = Decimal(str(beta_value)) * Decimal(str(portfolio_equity))

        # Check if record exists
        existing_stmt = select(FactorExposure).where(
            and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.factor_id == factor_id,
                FactorExposure.calculation_date == calculation_date
            )
        )
        existing_result = await db.execute(existing_stmt)
        existing_record = existing_result.scalar_one_or_none()

        if existing_record:
            existing_record.exposure_value = Decimal(str(beta_value))
            existing_record.exposure_dollar = exposure_dollar
        else:
            new_record = FactorExposure(
                id=uuid.uuid4(),
                portfolio_id=portfolio_id,
                factor_id=factor_id,
                calculation_date=calculation_date,
                exposure_value=Decimal(str(beta_value)),
                exposure_dollar=exposure_dollar
            )
            db.add(new_record)

        results['records_stored'] += 1
        results['factors_stored'].append(factor_name)

    logger.info(f"Stored {results['records_stored']} portfolio spread exposures")
    return results


def _build_skip_result(
    portfolio_id: UUID,
    calculation_date: date,
    context: PortfolioContext,
    reason: str
) -> Dict[str, Any]:
    """Build a standardized skip result for graceful degradation."""
    counts = context.get_position_count_summary()

    return {
        'success': True,
        'skipped': True,
        'reason': reason,
        'factor_betas': {},
        'position_betas': {},
        'data_quality': {
            **get_default_data_quality(),
            'skip_reason': reason,
            'positions_total': counts['total'],
            'positions_private': counts['private'],
            'portfolio_equity': float(context.equity_balance)
        },
        'metadata': {
            'calculation_date': calculation_date.isoformat(),
            'portfolio_id': str(portfolio_id),
            'method': 'OLS_SPREAD',
            'status': f'SKIPPED_{reason.upper()}'
        },
        'storage_results': get_default_storage_results(),
        'spread_diagnostics': {'status': 'skipped', 'reason': reason}
    }
