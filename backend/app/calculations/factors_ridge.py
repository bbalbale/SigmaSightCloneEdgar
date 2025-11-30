"""
Ridge Regression Factor Analysis - 6 Non-Market Factors Only
Addresses multicollinearity in style/quality factors using L2 regularization

IMPORTANT: This module handles ONLY the 6 non-market factors:
- Value, Growth, Momentum, Quality, Size, Low Volatility

Market Beta is calculated SEPARATELY via market_beta.py (simple OLS against SPY).

ARCHITECTURE: Position-First with Caching (November 2025)
================================================================================
This module follows the position-first calculation pattern:
  1. Check cache: which positions already have 6 style factors for this date?
  2. Calculate Ridge regression ONLY for uncached positions
  3. Persist position-level results immediately after each calculation
  4. Load cached + newly calculated betas for portfolio aggregation
  5. Store portfolio-level aggregates

This avoids recalculating betas for positions shared across multiple portfolios.
Same pattern as market_beta.py and interest_rate_beta.py.

Key improvements over OLS (factors.py):
- Ridge regression reduces VIF from 299 to ~15-20
- Fixes sign-flip issues in correlated factors
- Excludes Market beta (handled separately)
- Adds regularization_alpha and method='ridge' to database records
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from app.models.positions import Position
from app.models.market_data import FactorDefinition, FactorExposure
from app.calculations.market_data import get_position_value, get_returns
from app.calculations.regression_utils import classify_r_squared
from app.calculations.factor_utils import (
    get_default_storage_results,
    get_default_data_quality,
    normalize_factor_name,
    PortfolioContext,
    load_portfolio_context,
    # Position-first infrastructure
    bulk_load_cached_position_factors,
    persist_position_factor_betas,
    calculate_position_weights,
    aggregate_position_betas_to_portfolio,
)
from app.constants.factors import (
    REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS,
    BETA_CAP_LIMIT, QUALITY_FLAG_FULL_HISTORY,
    QUALITY_FLAG_LIMITED_HISTORY, QUALITY_FLAG_NO_PUBLIC_POSITIONS
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Ridge regression calculates exactly these 6 style factors
# (Market Beta and IR Beta are calculated by their own dedicated modules)
RIDGE_STYLE_FACTORS = {
    "Value": "VTV",
    "Growth": "VUG",
    "Momentum": "MTUM",
    "Quality": "QUAL",
    "Size": "IWM",
    "Low Volatility": "USMV",
}

EXPECTED_RIDGE_FACTOR_COUNT = 6


def calculate_single_position_ridge_betas(
    position_returns: pd.Series,
    factor_returns: pd.DataFrame,
    regularization_alpha: float = 1.0
) -> Dict[str, Any]:
    """
    Calculate Ridge regression factor betas for a single position.

    This is the core calculation function - it runs Ridge regression on
    a single position's returns against the 6 style factor returns.

    Args:
        position_returns: Daily returns for the position (pd.Series with date index)
        factor_returns: Daily returns for 6 style factors (pd.DataFrame with date index)
        regularization_alpha: L2 penalty strength (default 1.0)

    Returns:
        Dictionary containing:
        - betas: Dict mapping factor names to beta values
        - r_squared: Model fit quality
        - observations: Number of data points used
        - success: Whether regression succeeded
        - error: Error message if failed
    """
    # Align position and factor returns on common dates
    data = pd.concat([position_returns, factor_returns], axis=1).dropna()

    if len(data) < MIN_REGRESSION_DAYS:
        return {
            'betas': {fn: 0.0 for fn in factor_returns.columns},
            'r_squared': 0.0,
            'observations': len(data),
            'success': False,
            'error': f'Insufficient data: {len(data)} days (minimum: {MIN_REGRESSION_DAYS})'
        }

    y = data.iloc[:, 0].values  # Position returns
    X = data.iloc[:, 1:]         # Factor returns

    # Check degrees of freedom
    if X.shape[0] <= X.shape[1]:
        return {
            'betas': {fn: 0.0 for fn in factor_returns.columns},
            'r_squared': 0.0,
            'observations': len(data),
            'success': False,
            'error': f'Insufficient degrees of freedom: {X.shape[0]} obs vs {X.shape[1]} factors'
        }

    try:
        # Standardize features for Ridge regression (best practice)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Fit Ridge regression
        ridge_model = Ridge(alpha=regularization_alpha, fit_intercept=True)
        ridge_model.fit(X_scaled, y)

        # Calculate R-squared
        y_pred = ridge_model.predict(X_scaled)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Extract and transform betas back to original scale
        betas_scaled = ridge_model.coef_
        betas = betas_scaled / scaler.scale_

        # Apply beta caps and build result
        factor_betas = {}
        for idx, factor_name in enumerate(X.columns):
            raw_beta = float(betas[idx])

            if not np.isfinite(raw_beta):
                raw_beta = 0.0

            capped_beta = max(-BETA_CAP_LIMIT, min(BETA_CAP_LIMIT, raw_beta))

            if abs(raw_beta) > BETA_CAP_LIMIT:
                logger.debug(
                    f"Beta capped for factor {factor_name}: {raw_beta:.3f} -> {capped_beta:.3f}"
                )

            factor_betas[factor_name] = capped_beta

        return {
            'betas': factor_betas,
            'r_squared': float(r_squared),
            'observations': len(data),
            'success': True,
            'error': None
        }

    except Exception as e:
        logger.error(f"Ridge regression failed: {e}")
        return {
            'betas': {fn: 0.0 for fn in factor_returns.columns},
            'r_squared': 0.0,
            'observations': len(data),
            'success': False,
            'error': str(e)
        }


async def calculate_factor_betas_ridge(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    regularization_alpha: float = 1.0,
    use_delta_adjusted: bool = False,
    context: Optional[PortfolioContext] = None,
    price_cache=None
) -> Dict[str, Any]:
    """
    Calculate portfolio factor betas using Ridge regression (L2 regularization).

    ARCHITECTURE: Position-First with Caching
    =========================================
    1. Load portfolio context (positions, equity, factor definitions)
    2. Check cache: which positions already have 6 style factors for this date?
    3. Fetch factor ETF returns (VTV, VUG, MTUM, QUAL, IWM, USMV)
    4. Fetch position returns for uncached positions only
    5. Run Ridge regression for each uncached position
    6. Persist position-level betas immediately after calculation
    7. Load all position betas (cached + newly calculated)
    8. Aggregate to portfolio level using equity weights
    9. Store portfolio-level factor exposures

    This pattern matches market_beta.py and interest_rate_beta.py.

    Args:
        db: Database session
        portfolio_id: Portfolio ID to analyze
        calculation_date: Date for the calculation (end of regression window)
        regularization_alpha: L2 penalty strength (default 1.0)
        use_delta_adjusted: Use delta-adjusted exposures for options (not implemented)
        context: Pre-loaded portfolio context (optional)
        price_cache: Optional PriceCache for optimized price lookups

    Returns:
        Dictionary containing:
        - factor_betas: Portfolio-level factor betas
        - position_betas: Position-level factor betas (all positions)
        - data_quality: Quality metrics
        - metadata: Calculation metadata
        - storage_results: Database storage results
        - ridge_diagnostics: Ridge-specific diagnostics
    """
    logger.info(
        f"Calculating Ridge factor betas for portfolio {portfolio_id} "
        f"as of {calculation_date} with alpha={regularization_alpha}"
    )

    # Step 1: Load context if not provided
    if context is None:
        logger.info("Loading portfolio context")
        context = await load_portfolio_context(db, portfolio_id, calculation_date)

    # Get PUBLIC equity positions only (Ridge doesn't apply to PRIVATE or OPTIONS)
    public_positions = [
        p for p in context.public_positions
        if p.investment_class == 'PUBLIC' and p.position_type.value in ('LONG', 'SHORT')
    ]

    if not public_positions:
        counts = context.get_position_count_summary()
        logger.info(
            f"No PUBLIC equity positions for portfolio {portfolio_id} - skipping ridge factors. "
            f"Position counts: {counts}"
        )
        return _build_skip_result(portfolio_id, calculation_date, regularization_alpha, context, 'no_public_positions')

    position_ids = [p.id for p in public_positions]
    logger.info(f"Found {len(position_ids)} PUBLIC equity positions for Ridge calculation")

    # Step 2: Check cache - which positions already have 6 style factors?
    cached_betas = await bulk_load_cached_position_factors(
        db=db,
        position_ids=position_ids,
        calculation_method='ridge_regression',
        calculation_date=calculation_date,
        expected_factor_count=EXPECTED_RIDGE_FACTOR_COUNT
    )

    positions_needing_calculation = [
        p for p in public_positions
        if p.id not in cached_betas
    ]

    logger.info(
        f"Cache check: {len(cached_betas)} positions cached, "
        f"{len(positions_needing_calculation)} need calculation"
    )

    # Step 3: Fetch factor ETF returns
    end_date = calculation_date
    start_date = end_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)

    factor_symbols = list(RIDGE_STYLE_FACTORS.values())
    factor_returns = await get_returns(
        db=db,
        symbols=factor_symbols,
        start_date=start_date,
        end_date=end_date,
        align_dates=True,
        price_cache=price_cache
    )

    if factor_returns.empty:
        logger.error("No factor ETF returns available")
        return _build_skip_result(portfolio_id, calculation_date, regularization_alpha, context, 'no_factor_data')

    # Map ETF symbols to factor names
    symbol_to_factor = {v: k for k, v in RIDGE_STYLE_FACTORS.items()}
    factor_returns = factor_returns.rename(columns=symbol_to_factor)

    logger.info(f"Factor returns: {len(factor_returns)} days, factors: {list(factor_returns.columns)}")

    # Step 4 & 5: Calculate Ridge betas for uncached positions
    newly_calculated_betas: Dict[UUID, Dict[str, float]] = {}
    ridge_diagnostics = {
        'alpha': regularization_alpha,
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
            # Align factor and position returns
            common_dates = factor_returns.index.intersection(position_returns_df.index)
            factor_returns_aligned = factor_returns.loc[common_dates]

            total_r_squared = 0.0
            quality_flag = QUALITY_FLAG_FULL_HISTORY if len(common_dates) >= MIN_REGRESSION_DAYS else QUALITY_FLAG_LIMITED_HISTORY

            for position in positions_needing_calculation:
                if position.symbol not in position_returns_df.columns:
                    logger.debug(f"No return data for {position.symbol}")
                    ridge_diagnostics['positions_failed'] += 1
                    continue

                pos_returns = position_returns_df[position.symbol].loc[common_dates]

                # Run Ridge regression
                result = calculate_single_position_ridge_betas(
                    position_returns=pos_returns,
                    factor_returns=factor_returns_aligned,
                    regularization_alpha=regularization_alpha
                )

                if result['success']:
                    newly_calculated_betas[position.id] = result['betas']
                    ridge_diagnostics['positions_calculated'] += 1
                    total_r_squared += result['r_squared']

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
                    logger.debug(f"Ridge failed for {position.symbol}: {result['error']}")
                    ridge_diagnostics['positions_failed'] += 1

            # Commit after all positions are processed
            await db.commit()

            if ridge_diagnostics['positions_calculated'] > 0:
                ridge_diagnostics['avg_r_squared'] = total_r_squared / ridge_diagnostics['positions_calculated']

    logger.info(
        f"Ridge calculation complete: {ridge_diagnostics['positions_calculated']} calculated, "
        f"{ridge_diagnostics['positions_from_cache']} from cache, "
        f"{ridge_diagnostics['positions_failed']} failed"
    )

    # Step 7: Combine cached + newly calculated betas
    all_position_betas = {**cached_betas, **newly_calculated_betas}

    if not all_position_betas:
        logger.warning("No position betas available (all failed or no data)")
        return _build_skip_result(portfolio_id, calculation_date, regularization_alpha, context, 'no_position_betas')

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

    logger.info(f"Portfolio betas: {portfolio_betas}")

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
    # Convert position IDs to strings for JSON serialization
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
            'positions_from_cache': ridge_diagnostics['positions_from_cache'],
            'positions_calculated': ridge_diagnostics['positions_calculated'],
            'factors_processed': EXPECTED_RIDGE_FACTOR_COUNT
        },
        'metadata': {
            'calculation_date': calculation_date.isoformat(),
            'portfolio_id': str(portfolio_id),
            'method': 'ridge',
            'regularization_alpha': regularization_alpha,
            'regression_window_days': REGRESSION_WINDOW_DAYS
        },
        'storage_results': {
            'position_storage': {
                'records_stored': ridge_diagnostics['positions_calculated'] * EXPECTED_RIDGE_FACTOR_COUNT,
                'positions_from_cache': ridge_diagnostics['positions_from_cache']
            },
            'portfolio_storage': portfolio_storage
        },
        'ridge_diagnostics': ridge_diagnostics
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
    Store portfolio-level factor exposures to FactorExposure table.

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
        mapped_name = normalize_factor_name(factor_name)

        if mapped_name not in context.factor_name_to_id:
            results['errors'].append(f"Factor '{mapped_name}' not found in database")
            continue

        factor_id = context.factor_name_to_id[mapped_name]
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
        results['factors_stored'].append(mapped_name)

    logger.info(f"Stored {results['records_stored']} portfolio factor exposures")
    return results


def _build_skip_result(
    portfolio_id: UUID,
    calculation_date: date,
    regularization_alpha: float,
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
            'method': 'ridge',
            'regularization_alpha': regularization_alpha,
            'status': f'SKIPPED_{reason.upper()}'
        },
        'storage_results': get_default_storage_results(),
        'ridge_diagnostics': {'status': 'skipped', 'reason': reason}
    }


async def tune_ridge_alpha(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    alpha_range: Optional[List[float]] = None,
    context: Optional[PortfolioContext] = None
) -> Dict[str, Any]:
    """
    Test multiple alpha values and return comparison metrics.

    Helps choose optimal regularization strength for this portfolio.

    Args:
        db: Database session
        portfolio_id: Portfolio ID to analyze
        calculation_date: Date for calculation
        alpha_range: List of alpha values to test (default: [0.01, 0.1, 1.0, 5.0, 10.0])
        context: Pre-loaded portfolio context (optional)

    Returns:
        Dictionary with alpha comparison results and recommended alpha
    """
    if alpha_range is None:
        alpha_range = [0.01, 0.1, 1.0, 5.0, 10.0]

    logger.info(f"Tuning Ridge alpha for portfolio {portfolio_id}, testing {len(alpha_range)} values")

    # Load context once for all iterations
    if context is None:
        context = await load_portfolio_context(db, portfolio_id, calculation_date)

    tuning_results = []

    for alpha in alpha_range:
        logger.info(f"Testing alpha={alpha}")

        try:
            result = await calculate_factor_betas_ridge(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                regularization_alpha=alpha,
                use_delta_adjusted=False,
                context=context
            )

            tuning_results.append({
                'alpha': alpha,
                'avg_r_squared': result['ridge_diagnostics'].get('avg_r_squared', 0.0),
                'positions_processed': result['data_quality'].get('positions_processed', 0)
            })

        except Exception as e:
            logger.error(f"Error testing alpha={alpha}: {str(e)}")
            tuning_results.append({
                'alpha': alpha,
                'error': str(e)
            })

    # Find optimal alpha (maximize R² while minimizing overfitting)
    valid_results = [r for r in tuning_results if 'error' not in r and r['alpha'] >= 0.1]

    if valid_results:
        optimal_result = max(valid_results, key=lambda x: x['avg_r_squared'])
        recommended_alpha = optimal_result['alpha']
    else:
        recommended_alpha = 1.0  # Default fallback

    return {
        'tuning_results': tuning_results,
        'recommended_alpha': recommended_alpha,
        'alpha_range_tested': alpha_range,
        'portfolio_id': str(portfolio_id),
        'calculation_date': calculation_date.isoformat()
    }
