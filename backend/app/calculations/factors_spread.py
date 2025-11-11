"""
Spread Factor Analysis - Long-Short Factor Betas
Calculates portfolio exposure to 4 long-short spread factors using 180-day OLS regression.

Addresses multicollinearity by using factor spreads instead of raw factor ETFs:
- Growth-Value Spread (VUG - VTV): ~0.3 correlation with market (vs 0.93+ for raw)
- Momentum Spread (MTUM - SPY): Independent momentum exposure
- Size Spread (IWM - SPY): Small vs large cap tilt
- Quality Spread (QUAL - SPY): Quality vs market exposure

Created: 2025-10-20
Architecture: 4 separate OLS regressions (one per spread factor)
Regression Window: 180 days (6 months)
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.positions import Position
from app.models.market_data import MarketDataCache, FactorDefinition
from app.constants.factors import (
    SPREAD_FACTORS, SPREAD_REGRESSION_WINDOW_DAYS,
    SPREAD_MIN_REGRESSION_DAYS, BETA_CAP_LIMIT
)
from app.calculations.factor_utils import (
    PortfolioContext, load_portfolio_context,
    get_default_data_quality,
    get_default_storage_results
)
from app.calculations.market_data import get_position_value, get_returns
from app.calculations.regression_utils import run_single_factor_regression
from app.core.logging import get_logger

logger = get_logger(__name__)


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
        price_cache: Optional PriceCache for optimized price lookups (300x speedup)

    Returns:
        DataFrame with 4 columns (spread factor names) and date index.
        Each cell contains the daily spread return for that factor.

    Example:
        VUG return = 1.5%, VTV return = 0.8%
        → Growth-Value Spread return = 1.5% - 0.8% = 0.7%

    Phase 8 Refactoring:
        Now uses canonical get_returns() instead of manual price fetching + pct_change.
        This eliminates ~50 lines of duplicate code and ensures consistent return calculation.
    """
    logger.info(f"Fetching spread returns from {start_date} to {end_date}")

    # Collect all unique ETF symbols needed
    etf_symbols = set()
    for long_etf, short_etf in SPREAD_FACTORS.values():
        etf_symbols.add(long_etf)
        etf_symbols.add(short_etf)

    logger.info(f"Fetching returns for {len(etf_symbols)} ETFs: {etf_symbols}")

    # Use canonical get_returns() function instead of manual price fetching
    # This replaces ~30 lines of duplicate "fetch prices → pct_change" logic
    logger.info(f"[TRACE] Calling get_returns for {list(etf_symbols)} from {start_date} to {end_date}")
    returns = await get_returns(
        db=db,
        symbols=list(etf_symbols),
        start_date=start_date,
        end_date=end_date,
        align_dates=True,  # Drop dates with any missing data
        price_cache=price_cache  # Pass through cache for optimization
    )

    logger.info(f"[TRACE] get_returns returned: empty={returns.empty}, shape={returns.shape if not returns.empty else 'N/A'}")
    if not returns.empty:
        logger.info(f"[TRACE] Columns in returns: {list(returns.columns)}")
        logger.info(f"[TRACE] Date range in returns: {returns.index[0]} to {returns.index[-1]}")

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


async def calculate_position_spread_beta(
    position_returns: pd.Series,
    spread_returns: pd.Series,
    spread_name: str
) -> Dict[str, Any]:
    """
    Calculate single spread beta using canonical run_single_factor_regression().

    This function runs a simple univariate OLS regression:
        position_return = alpha + beta * spread_return + error

    Args:
        position_returns: Position daily returns (aligned)
        spread_returns: Spread factor daily returns (aligned)
        spread_name: Name of spread factor (for logging)

    Returns:
        Dict with:
        - beta: Regression coefficient
        - r_squared: Model fit quality
        - std_error: Standard error of beta
        - p_value: Statistical significance
        - observations: Number of data points
        - success: Whether regression succeeded

    Phase 8 Refactoring:
        Now uses canonical run_single_factor_regression() instead of manual OLS.
        This eliminates ~70 lines of duplicate regression code and ensures consistent
        beta capping, significance testing, and error handling.
    """
    # Align on common dates
    data = pd.concat([position_returns, spread_returns], axis=1).dropna()

    if len(data) < SPREAD_MIN_REGRESSION_DAYS:
        logger.warning(
            f"Insufficient data for {spread_name}: {len(data)} days "
            f"(minimum: {SPREAD_MIN_REGRESSION_DAYS})"
        )
        return {
            'beta': 0.0,
            'r_squared': 0.0,
            'std_error': 0.0,
            'p_value': 1.0,
            'observations': len(data),
            'success': False,
            'error': f'Insufficient data: {len(data)} days'
        }

    # Extract aligned returns
    y = data.iloc[:, 0].values  # Position returns
    x = data.iloc[:, 1].values  # Spread returns

    try:
        # Use canonical regression function instead of manual statsmodels OLS
        # This replaces ~40 lines of duplicate code (OLS setup, beta capping, error handling)
        regression_result = run_single_factor_regression(
            y=y,
            x=x,
            cap=BETA_CAP_LIMIT,  # Cap beta at ±5.0
            confidence=0.10,     # 90% confidence level (relaxed)
            return_diagnostics=True
        )

        logger.debug(
            f"{spread_name} regression: beta={regression_result['beta']:.3f}, "
            f"R²={regression_result['r_squared']:.3f}, "
            f"p={regression_result['p_value']:.3f}, n={len(data)}"
        )

        return {
            'beta': regression_result['beta'],
            'alpha': regression_result['alpha'],
            'r_squared': regression_result['r_squared'],
            'std_error': regression_result['std_error'],
            'p_value': regression_result['p_value'],
            'observations': len(data),
            'success': True
        }

    except Exception as e:
        logger.error(f"OLS regression failed for {spread_name}: {e}")
        return {
            'beta': 0.0,
            'r_squared': 0.0,
            'std_error': 0.0,
            'p_value': 1.0,
            'observations': len(data),
            'success': False,
            'error': str(e)
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

    This is the main entry point for spread factor calculation. It orchestrates:
    1. Fetching spread returns (VUG-VTV, MTUM-SPY, IWM-SPY, QUAL-SPY)
    2. Fetching position returns (reuse from factors.py)
    3. Running 4 separate OLS regressions for each position
    4. Aggregating to portfolio level (equity-weighted)
    5. Storing results in factor_exposures tables

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        calculation_date: Calculation date (end of regression window)
        context: Pre-loaded portfolio context (optional, for performance)
        price_cache: Optional PriceCache for optimized price lookups (300x speedup)

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

    # Load context if not provided
    if context is None:
        logger.info("Loading portfolio context")
        context = await load_portfolio_context(db, portfolio_id, calculation_date)

    # Define regression window (180 days + 30-day buffer for trading days)
    end_date = calculation_date
    start_date = end_date - timedelta(days=SPREAD_REGRESSION_WINDOW_DAYS + 30)

    logger.info(f"Regression window: {start_date} to {end_date}")

    try:
        # Step 1: Fetch spread returns
        spread_returns = await fetch_spread_returns(db, start_date, end_date, price_cache)

        if spread_returns.empty:
            raise ValueError("No spread returns data available")

        logger.info(f"Spread returns: {len(spread_returns)} days, {len(spread_returns.columns)} factors")

        # Step 2: Fetch position returns (reuse from factors.py)
        from app.calculations.factors import calculate_position_returns

        position_returns = await calculate_position_returns(
            db=db,
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
            use_delta_adjusted=False,
            context=context
        )

        if position_returns.empty:
            counts = context.get_position_count_summary()
            logger.warning(
                f"No position returns available for portfolio {portfolio_id}. "
                f"Position counts: {counts}"
            )
            return {
                'factor_betas': {},
                'position_betas': {},
                'data_quality': {
                    **get_default_data_quality(),
                    'positions_total': counts['total'],
                    'positions_private': counts['private'],
                    'skip_reason': 'NO_POSITION_RETURNS'
                },
                'metadata': {
                    'calculation_date': calculation_date.isoformat(),
                    'status': 'SKIPPED_NO_POSITIONS',
                    'regression_window_days': SPREAD_REGRESSION_WINDOW_DAYS,
                    'portfolio_id': str(portfolio_id)
                },
                'storage_results': get_default_storage_results()
            }

        logger.info(f"Position returns: {len(position_returns)} days, {len(position_returns.columns)} positions")

        # Step 3: Align dates
        common_dates = spread_returns.index.intersection(position_returns.index)

        if len(common_dates) < SPREAD_MIN_REGRESSION_DAYS:
            logger.warning(
                f"Insufficient aligned data: {len(common_dates)} days "
                f"(minimum: {SPREAD_MIN_REGRESSION_DAYS})"
            )

        spread_returns_aligned = spread_returns.loc[common_dates]
        position_returns_aligned = position_returns.loc[common_dates]

        logger.info(f"Aligned data: {len(common_dates)} common trading days")

        # Step 4: Calculate spread betas for each position
        position_betas = {}  # {position_id: {spread_name: beta}}
        regression_stats = {}
        skipped_count = 0
        successful_count = 0

        for position_id in position_returns_aligned.columns:
            position_betas[position_id] = {}
            regression_stats[position_id] = {}

            pos_returns = position_returns_aligned[position_id]

            # Run 4 separate OLS regressions
            for spread_name in SPREAD_FACTORS.keys():
                spread_ret = spread_returns_aligned[spread_name]

                result = await calculate_position_spread_beta(
                    position_returns=pos_returns,
                    spread_returns=spread_ret,
                    spread_name=spread_name
                )

                # Only store betas from successful regressions
                if result.get('success', False):
                    position_betas[position_id][spread_name] = result['beta']
                    successful_count += 1
                else:
                    # Log skip reason but don't store zero beta
                    skipped_count += 1
                    logger.debug(
                        f"Skipped {spread_name} for position {position_id}: "
                        f"{result.get('error', 'Unknown error')}"
                    )

                # Always store regression stats for debugging
                regression_stats[position_id][spread_name] = result

        # Clean up: Remove positions with no successful regressions
        positions_with_no_data = [
            pos_id for pos_id, betas in position_betas.items()
            if len(betas) == 0
        ]
        for pos_id in positions_with_no_data:
            del position_betas[pos_id]

        if positions_with_no_data:
            logger.info(
                f"Removed {len(positions_with_no_data)} positions with no successful regressions"
            )

        logger.info(
            f"Spread beta calculation: {successful_count} successful, "
            f"{skipped_count} skipped (insufficient data), "
            f"{len(position_betas)} positions with at least one valid beta"
        )

        # DEBUG: Log position_betas contents
        logger.info(f"[DEBUG] position_betas keys: {list(position_betas.keys())[:5]}... (showing first 5)")
        logger.info(f"[DEBUG] position_betas sample: {dict(list(position_betas.items())[:2])}")
        for pid, betas in list(position_betas.items())[:3]:
            logger.info(f"[DEBUG] Position {pid}: {betas}")

        # Step 5: Aggregate to portfolio level (equity-weighted)
        from app.calculations.factors import _aggregate_portfolio_betas

        portfolio_betas = await _aggregate_portfolio_betas(
            db=db,
            portfolio_id=portfolio_id,
            position_betas=position_betas,
            context=context
        )

        logger.info(f"Portfolio-level spread betas: {portfolio_betas}")

        # DEBUG: Log what's being passed to storage
        logger.info(f"[DEBUG] BEFORE STORAGE: position_betas has {len(position_betas)} positions")
        logger.info(f"[DEBUG] BEFORE STORAGE: portfolio_betas has {len(portfolio_betas)} factors")
        logger.info(f"[DEBUG] BEFORE STORAGE: position_betas is empty? {len(position_betas) == 0}")
        if len(position_betas) > 0:
            logger.info(f"[DEBUG] BEFORE STORAGE: First position in position_betas: {list(position_betas.items())[0]}")

        # Step 6: Store in database
        storage_results = await store_spread_factor_exposures(
            db=db,
            portfolio_id=portfolio_id,
            position_betas=position_betas,
            portfolio_betas=portfolio_betas,
            calculation_date=calculation_date,
            context=context
        )

        # DEBUG: Log storage results
        logger.info(f"[DEBUG] AFTER STORAGE: storage_results = {storage_results}")

        # Step 7: Prepare results
        results = {
            'factor_betas': portfolio_betas,
            'position_betas': position_betas,
            'data_quality': {
                'regression_days': len(common_dates),
                'required_days': SPREAD_MIN_REGRESSION_DAYS,
                'positions_processed': len(position_betas),
                'factors_processed': len(SPREAD_FACTORS),
                'successful_regressions': successful_count,
                'skipped_regressions': skipped_count,
                'success_rate': successful_count / (successful_count + skipped_count) if (successful_count + skipped_count) > 0 else 0.0
            },
            'metadata': {
                'calculation_date': calculation_date.isoformat(),
                'start_date': common_dates[0].isoformat() if len(common_dates) > 0 else None,
                'end_date': common_dates[-1].isoformat() if len(common_dates) > 0 else None,
                'regression_window_days': SPREAD_REGRESSION_WINDOW_DAYS,
                'portfolio_id': str(portfolio_id),
                'method': 'OLS_SPREAD'
            },
            'regression_stats': regression_stats,
            'storage_results': storage_results
        }

        logger.info(
            f"[OK] Spread factor calculation complete: "
            f"{len(position_betas)} positions, {len(portfolio_betas)} portfolio factors"
        )

        return results

    except Exception as e:
        logger.error(f"[ERROR] Error calculating spread factor betas: {e}", exc_info=True)
        raise


async def store_spread_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    position_betas: Dict[UUID, Dict[str, float]],
    portfolio_betas: Dict[str, float],
    calculation_date: date,
    context: PortfolioContext
) -> Dict[str, Any]:
    """
    Store spread factor exposures in factor_exposures tables.

    Reuses existing storage functions from factors.py since spread factors
    are stored in the same tables (just with factor_type='spread').

    Args:
        db: Database session
        portfolio_id: Portfolio UUID
        position_betas: Position-level betas {position_id: {factor_name: beta}}
        portfolio_betas: Portfolio-level betas {factor_name: beta}
        calculation_date: Calculation date
        context: Portfolio context

    Returns:
        Dict with storage results (records stored, etc.)
    """
    from app.calculations.factors import (
        store_position_factor_exposures,
        aggregate_portfolio_factor_exposures
    )

    storage_results = {}

    # DEBUG: Log what was received
    logger.info(f"[DEBUG] store_spread_factor_exposures RECEIVED: position_betas has {len(position_betas)} positions")
    logger.info(f"[DEBUG] store_spread_factor_exposures RECEIVED: portfolio_betas has {len(portfolio_betas)} factors")

    # Store position-level exposures
    if position_betas:
        logger.info(f"[DEBUG] ENTERING position-level storage block with {len(position_betas)} positions")
        logger.info("Storing position-level spread factor exposures")
        position_storage = await store_position_factor_exposures(
            db=db,
            position_betas=position_betas,
            calculation_date=calculation_date,
            quality_flag='full_history',
            context=context
        )
        storage_results['position_storage'] = position_storage
        logger.info(f"[OK] Stored {position_storage['records_stored']} position spread betas")
    else:
        logger.warning(f"[DEBUG] SKIPPING position-level storage - position_betas is empty or False!")
        logger.warning(f"[DEBUG] position_betas type: {type(position_betas)}, len: {len(position_betas) if position_betas else 'N/A'}")

    # Store portfolio-level exposures
    if portfolio_betas:
        logger.info("Storing portfolio-level spread factor exposures")

        # Build position dicts for aggregation
        position_dicts = []
        for pos in context.active_positions:
            market_value = float(get_position_value(pos, signed=False, recalculate=False))
            position_dicts.append({
                'symbol': pos.symbol,
                'quantity': float(pos.quantity),
                'market_value': market_value,
                'exposure': market_value,
                'position_type': pos.position_type.value if pos.position_type else 'LONG',
                'last_price': float(pos.last_price) if pos.last_price else 0
            })

        from app.calculations.portfolio import calculate_portfolio_exposures
        portfolio_exposures = calculate_portfolio_exposures(position_dicts) if position_dicts else {}

        portfolio_storage = await aggregate_portfolio_factor_exposures(
            db=db,
            position_betas=position_betas,
            portfolio_exposures=portfolio_exposures,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            context=context
        )
        storage_results['portfolio_storage'] = portfolio_storage
        logger.info("[OK] Portfolio spread betas stored successfully")

    return storage_results
