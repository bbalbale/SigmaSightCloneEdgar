"""
Spread Factor Analysis - Long-Short Factor Betas
Calculates portfolio exposure to 4 long-short spread factors using 180-day OLS regression.

Addresses multicollinearity by using factor spreads instead of raw factor ETFs:
- Growth-Value Spread (VUG - VTV): ~0.3 correlation with market (vs 0.93+ for raw)
- Momentum Spread (MTUM - SPY): Independent momentum exposure
- Size Spread (IWM - SPY): Small vs large cap tilt
- Quality Spread (QUAL - SPY): Quality vs market exposure

ARCHITECTURE: Position-First with Caching (November 2025)
================================================================================
This module follows the position-first calculation pattern:
  1. Check cache: which positions already have 4 spread factors for this date?
  2. Calculate OLS regression ONLY for uncached positions
  3. Persist position-level results immediately after each calculation
  4. Load cached + newly calculated betas for portfolio aggregation
  5. Store portfolio-level aggregates

This avoids recalculating betas for positions shared across multiple portfolios.
Same pattern as market_beta.py, interest_rate_beta.py, and factors_ridge.py.

Created: 2025-10-20
Updated: 2025-11-30 (Position-first refactoring)
Regression Window: 180 days (6 months)
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
from app.models.market_data import FactorDefinition, FactorExposure
from app.constants.factors import (
    SPREAD_FACTORS, SPREAD_REGRESSION_WINDOW_DAYS,
    SPREAD_MIN_REGRESSION_DAYS, BETA_CAP_LIMIT,
    QUALITY_FLAG_FULL_HISTORY, QUALITY_FLAG_LIMITED_HISTORY,
    QUALITY_FLAG_NO_PUBLIC_POSITIONS
)
from app.calculations.factor_utils import (
    PortfolioContext, load_portfolio_context,
    get_default_data_quality,
    get_default_storage_results,
    normalize_factor_name,
    # Position-first infrastructure
    bulk_load_cached_position_factors,
    persist_position_factor_betas,
    calculate_position_weights,
    aggregate_position_betas_to_portfolio,
)
from app.calculations.market_data import get_position_value, get_returns
from app.calculations.regression_utils import run_single_factor_regression
from app.core.logging import get_logger

logger = get_logger(__name__)

# Spread factors: 4 long-short factor pairs
EXPECTED_SPREAD_FACTOR_COUNT = 4


async def fetch_spread_returns(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    price_cache=None
) -> pd.DataFrame:
    """
    Calculate daily returns for 4 spread factors.

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

    logger.info(f"Fetching returns for {len(etf_symbols)} ETFs: {etf_symbols}")

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
            logger.debug(
                f"{spread_name}: Long={long_etf}, Short={short_etf}, "
                f"Mean spread return={spread_returns[spread_name].mean():.4f}"
            )
        else:
            logger.warning(f"Missing data for {spread_name}: {long_etf} or {short_etf}")
            spread_returns[spread_name] = np.nan

    # Drop rows with any NaN values
    spread_returns = spread_returns.dropna()

    logger.info(
        f"Calculated spread returns for {len(spread_returns)} days, "
        f"{len(spread_returns.columns)} factors"
    )
    return spread_returns


def calculate_single_position_spread_betas(
    position_returns: pd.Series,
    spread_returns: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate all 4 spread betas for a single position using OLS regression.

    This is the core calculation function - it runs 4 separate univariate
    OLS regressions (one per spread factor) for a single position.

    Args:
        position_returns: Daily returns for the position (pd.Series with date index)
        spread_returns: Daily returns for 4 spread factors (pd.DataFrame with date index)

    Returns:
        Dictionary containing:
        - betas: Dict mapping spread factor names to beta values
        - avg_r_squared: Average R² across the 4 regressions
        - observations: Number of data points used
        - success: Whether at least one regression succeeded
        - successful_factors: List of factors with successful regressions
        - failed_factors: List of factors that failed
    """
    # Align position and spread returns on common dates
    data = pd.concat([position_returns, spread_returns], axis=1).dropna()

    if len(data) < SPREAD_MIN_REGRESSION_DAYS:
        return {
            'betas': {},
            'avg_r_squared': 0.0,
            'observations': len(data),
            'success': False,
            'successful_factors': [],
            'failed_factors': list(spread_returns.columns),
            'error': f'Insufficient data: {len(data)} days (minimum: {SPREAD_MIN_REGRESSION_DAYS})'
        }

    y = data.iloc[:, 0].values  # Position returns
    factor_betas = {}
    total_r_squared = 0.0
    successful_factors = []
    failed_factors = []

    # Run 4 separate OLS regressions (one per spread factor)
    for spread_name in spread_returns.columns:
        x = data[spread_name].values

        try:
            regression_result = run_single_factor_regression(
                y=y,
                x=x,
                cap=BETA_CAP_LIMIT,
                confidence=0.10,
                return_diagnostics=True
            )

            if regression_result.get('success', True):
                factor_betas[spread_name] = regression_result['beta']
                total_r_squared += regression_result['r_squared']
                successful_factors.append(spread_name)
            else:
                failed_factors.append(spread_name)

        except Exception as e:
            logger.debug(f"OLS regression failed for {spread_name}: {e}")
            failed_factors.append(spread_name)

    success = len(successful_factors) > 0
    avg_r_squared = total_r_squared / len(successful_factors) if successful_factors else 0.0

    return {
        'betas': factor_betas,
        'avg_r_squared': avg_r_squared,
        'observations': len(data),
        'success': success,
        'successful_factors': successful_factors,
        'failed_factors': failed_factors,
        'error': None if success else 'All regressions failed'
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
    6. Persist position-level betas immediately after calculation
    7. Load all position betas (cached + newly calculated)
    8. Aggregate to portfolio level using equity weights
    9. Store portfolio-level factor exposures

    This pattern matches market_beta.py, interest_rate_beta.py, and factors_ridge.py.

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Calculation date (end of regression window)
        context: Pre-loaded portfolio context (optional, for performance)
        price_cache: Optional PriceCache for optimized price lookups

    Returns:
        Dict with:
        - factor_betas: Portfolio-level spread betas
        - position_betas: Position-level spread betas
        - data_quality: Regression quality metrics
        - metadata: Calculation metadata
        - storage_results: Database storage results
    """
    logger.info(
        f"Calculating spread factor betas for portfolio {portfolio_id} "
        f"as of {calculation_date} (180-day window)"
    )

    # Step 1: Load context if not provided
    if context is None:
        logger.info("Loading portfolio context")
        context = await load_portfolio_context(db, portfolio_id, calculation_date)

    # Get PUBLIC equity positions only (Spread doesn't apply to PRIVATE or OPTIONS)
    public_positions = [
        p for p in context.public_positions
        if p.investment_class == 'PUBLIC' and p.position_type.value in ('LONG', 'SHORT')
    ]

    if not public_positions:
        counts = context.get_position_count_summary()
        logger.info(
            f"No PUBLIC equity positions for portfolio {portfolio_id} - skipping spread factors. "
            f"Position counts: {counts}"
        )
        return _build_skip_result(portfolio_id, calculation_date, context, 'no_public_positions')

    position_ids = [p.id for p in public_positions]
    logger.info(f"Found {len(position_ids)} PUBLIC equity positions for Spread calculation")

    # Step 2: Check cache - which positions already have 4 spread factors?
    cached_betas = await bulk_load_cached_position_factors(
        db=db,
        position_ids=position_ids,
        calculation_method='spread_regression',
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

    spread_returns = await fetch_spread_returns(db, start_date, end_date, price_cache)

    if spread_returns.empty:
        logger.error("No spread returns available")
        return _build_skip_result(portfolio_id, calculation_date, context, 'no_spread_data')

    logger.info(f"Spread returns: {len(spread_returns)} days, factors: {list(spread_returns.columns)}")

    # Step 4 & 5: Calculate spread betas for uncached positions
    newly_calculated_betas: Dict[UUID, Dict[str, float]] = {}
    spread_diagnostics = {
        'positions_from_cache': len(cached_betas),
        'positions_calculated': 0,
        'positions_failed': 0,
        'avg_r_squared': 0.0,
        'total_successful_regressions': 0,
        'total_failed_regressions': 0,
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
            quality_flag = QUALITY_FLAG_FULL_HISTORY if len(common_dates) >= SPREAD_MIN_REGRESSION_DAYS else QUALITY_FLAG_LIMITED_HISTORY

            for position in positions_needing_calculation:
                if position.symbol not in position_returns_df.columns:
                    logger.debug(f"No return data for {position.symbol}")
                    spread_diagnostics['positions_failed'] += 1
                    continue

                pos_returns = position_returns_df[position.symbol].loc[common_dates]

                # Run OLS regressions for all 4 spread factors
                result = calculate_single_position_spread_betas(
                    position_returns=pos_returns,
                    spread_returns=spread_returns_aligned
                )

                if result['success'] and result['betas']:
                    newly_calculated_betas[position.id] = result['betas']
                    spread_diagnostics['positions_calculated'] += 1
                    total_r_squared += result['avg_r_squared']
                    spread_diagnostics['total_successful_regressions'] += len(result['successful_factors'])
                    spread_diagnostics['total_failed_regressions'] += len(result['failed_factors'])

                    # Step 6: Persist immediately
                    await persist_position_factor_betas(
                        db=db,
                        position_id=position.id,
                        factor_betas=result['betas'],
                        calculation_date=calculation_date,
                        factor_name_to_id=context.factor_name_to_id,
                        quality_flag=quality_flag
                    )
                else:
                    logger.debug(f"Spread failed for {position.symbol}: {result.get('error', 'Unknown')}")
                    spread_diagnostics['positions_failed'] += 1

            # Commit after all positions are processed
            await db.commit()

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

    # Step 8: Aggregate to portfolio level using equity weights
    positions_with_betas = [p for p in public_positions if p.id in all_position_betas]
    position_weights = calculate_position_weights(
        positions=positions_with_betas,
        portfolio_equity=float(context.equity_balance)
    )

    portfolio_betas = aggregate_position_betas_to_portfolio(
        position_betas=all_position_betas,
        position_weights=position_weights
    )

    logger.info(f"Portfolio spread betas: {portfolio_betas}")

    # Step 9: Store portfolio-level factor exposures
    portfolio_storage = await _store_portfolio_factor_exposures(
        db=db,
        portfolio_id=portfolio_id,
        portfolio_betas=portfolio_betas,
        calculation_date=calculation_date,
        context=context
    )
    await db.commit()

    # Build results
    position_betas_serializable = {
        str(pid): betas for pid, betas in all_position_betas.items()
    }

    results = {
        'success': True,
        'factor_betas': portfolio_betas,
        'position_betas': position_betas_serializable,
        'data_quality': {
            'quality_flag': QUALITY_FLAG_FULL_HISTORY,
            'positions_processed': len(all_position_betas),
            'positions_from_cache': spread_diagnostics['positions_from_cache'],
            'positions_calculated': spread_diagnostics['positions_calculated'],
            'factors_processed': EXPECTED_SPREAD_FACTOR_COUNT,
            'total_successful_regressions': spread_diagnostics['total_successful_regressions'],
            'total_failed_regressions': spread_diagnostics['total_failed_regressions']
        },
        'metadata': {
            'calculation_date': calculation_date.isoformat(),
            'portfolio_id': str(portfolio_id),
            'method': 'spread_regression',
            'regression_window_days': SPREAD_REGRESSION_WINDOW_DAYS
        },
        'storage_results': {
            'position_storage': {
                'records_stored': spread_diagnostics['total_successful_regressions'],
                'positions_from_cache': spread_diagnostics['positions_from_cache']
            },
            'portfolio_storage': portfolio_storage
        },
        'spread_diagnostics': spread_diagnostics
    }

    return results


async def _store_portfolio_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    portfolio_betas: Dict[str, float],
    calculation_date: date,
    context: PortfolioContext
) -> Dict[str, Any]:
    """
    Store portfolio-level spread factor exposures to FactorExposure table.

    Uses upsert pattern (update if exists, insert if not).
    Does NOT commit - caller manages transaction.
    """
    import uuid

    results = {
        'records_stored': 0,
        'factors_stored': [],
        'errors': []
    }

    portfolio_equity = float(context.equity_balance)

    for factor_name, beta_value in portfolio_betas.items():
        # Spread factor names match database names directly
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

    logger.info(f"Stored {results['records_stored']} portfolio spread factor exposures")
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
            'quality_flag': QUALITY_FLAG_NO_PUBLIC_POSITIONS,
            'skip_reason': reason,
            'positions_total': counts['total'],
            'positions_private': counts['private'],
            'portfolio_equity': float(context.equity_balance)
        },
        'metadata': {
            'calculation_date': calculation_date.isoformat(),
            'portfolio_id': str(portfolio_id),
            'method': 'spread_regression',
            'status': f'SKIPPED_{reason.upper()}'
        },
        'storage_results': get_default_storage_results(),
        'spread_diagnostics': {'status': 'skipped', 'reason': reason}
    }
