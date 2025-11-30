"""
Shared utilities for factor analysis calculations

This module provides centralized utilities to:
- Normalize factor names between calculation and database
- Calculate position market values consistently
- Classify statistical metrics (R², significance)
- Provide default data structures for consistency
- Check multicollinearity in factor models
- Analyze factor correlations

Created: 2025-01-14
Part of Factor Analysis Enhancement Plan
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.factors import OPTIONS_MULTIPLIER
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# SECTION 1: FACTOR NAME NORMALIZATION
# ============================================================================

# Centralized factor name mapping (calculation name -> database name)
FACTOR_NAME_MAPPING = {
    'Market': 'Market Beta',
    'Value': 'Value',
    'Growth': 'Growth',
    'Momentum': 'Momentum',
    'Quality': 'Quality',
    'Size': 'Size',
    'Low Volatility': 'Low Volatility'
}


def normalize_factor_name(calc_name: str) -> str:
    """
    Normalize calculation factor name to database factor name.

    This provides a single source of truth for factor name mapping,
    eliminating duplicate mapping logic across functions.

    Args:
        calc_name: Factor name from regression (e.g., 'Market')

    Returns:
        Database factor name (e.g., 'Market Beta')

    Example:
        >>> normalize_factor_name('Market')
        'Market Beta'
        >>> normalize_factor_name('Value')
        'Value'
    """
    return FACTOR_NAME_MAPPING.get(calc_name, calc_name)


def get_inverse_factor_mapping() -> Dict[str, str]:
    """
    Get database factor name -> calculation name mapping.

    Returns:
        Dictionary mapping database names to calculation names
    """
    return {v: k for k, v in FACTOR_NAME_MAPPING.items()}


# ============================================================================
# SECTION 2: DEFAULT DATA STRUCTURES
# ============================================================================

def get_default_storage_results() -> Dict[str, Any]:
    """
    Get default storage results structure with consistent schema.

    This ensures skip and success cases have identical structure
    for easier API consumption and testing.

    Returns:
        Dictionary with storage results for position and portfolio levels
    """
    return {
        'position_storage': {
            'records_stored': 0,
            'positions_processed': 0,
            'errors': [],
            'skipped': False,
            'skip_reason': None
        },
        'portfolio_storage': {
            'records_stored': 0,
            'factors_processed': 0,
            'errors': [],
            'skipped': False,
            'skip_reason': None
        }
    }


def get_default_data_quality() -> Dict[str, Any]:
    """
    Get default data quality structure.

    Returns comprehensive quality metadata including:
    - Quality flag (FULL_HISTORY, LIMITED_HISTORY, etc.)
    - Position counts and classifications
    - Data availability metrics
    - Skip reasons and diagnostics

    Returns:
        Dictionary with data quality metrics
    """
    return {
        'quality_flag': None,
        'message': '',
        'positions_analyzed': 0,
        'positions_total': 0,
        'positions_private': 0,
        'positions_exited': 0,
        'data_days': 0,
        'regression_days': 0,
        'required_days': 0,
        'skip_reason': None,
        'calculation_attempted': True,
        'portfolio_equity': 0.0
    }


# ============================================================================
# SECTION 3: MARKET VALUE UTILITIES (DEPRECATED - Use market_data.py)
# ============================================================================
# Note: All market value utilities have been consolidated into market_data.py
# - Use market_data.get_position_value() for position valuation
# - Use market_data.is_options_position() for option detection


# ============================================================================
# SECTION 4: MULTICOLLINEARITY DIAGNOSTICS
# ============================================================================

def check_multicollinearity(X: pd.DataFrame) -> Dict[str, Any]:
    """
    Check for multicollinearity in factor matrix using VIF and condition number.

    When factors are highly correlated, regression beta estimates become:
    - Unstable (small data changes → large beta changes)
    - Unreliable (inflated standard errors)
    - Difficult to interpret

    Args:
        X: Factor returns matrix (n observations × k factors)

    Returns:
        Dictionary containing:
        - vif_values: Dict[factor_name, vif]
        - condition_number: float
        - warnings: List[str] of diagnostic messages
        - has_severe_multicollinearity: bool (any VIF > 10)
        - has_moderate_multicollinearity: bool (any VIF > 5)
        - max_vif: float

    Note:
        VIF (Variance Inflation Factor) measures how much variance is inflated
        due to correlation with other factors. VIF = 1/(1 - R²) where R² is
        from regressing factor i on all other factors.

        Academic standards:
        - VIF > 10: Severe multicollinearity (requires action)
        - VIF > 5: Moderate multicollinearity (investigate)
        - Condition number > 100: Multicollinearity present
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    vif_data = {}
    severe_factors = []
    moderate_factors = []

    # Calculate VIF for each factor
    for i, col in enumerate(X.columns):
        try:
            vif = variance_inflation_factor(X.values, i)
            vif_data[col] = float(vif) if np.isfinite(vif) else 999.9

            if vif > 10:
                severe_factors.append((col, vif))
            elif vif > 5:
                moderate_factors.append((col, vif))
        except Exception as e:
            # If VIF calculation fails (e.g., perfect collinearity)
            logger.warning(f"VIF calculation failed for {col}: {str(e)}")
            vif_data[col] = 999.9
            severe_factors.append((col, 999.9))

    # Calculate condition number
    try:
        condition_number = np.linalg.cond(X.values)
    except:
        condition_number = 999.9

    # Generate warnings
    warnings = []

    for factor, vif in severe_factors:
        warnings.append(
            f"{factor}: VIF={vif:.1f} (>10, severe multicollinearity - "
            f"consider removing or using ridge regression)"
        )

    for factor, vif in moderate_factors:
        warnings.append(
            f"{factor}: VIF={vif:.1f} (>5, moderate multicollinearity - "
            f"beta estimates may be unstable)"
        )

    if condition_number > 100:
        warnings.append(
            f"Condition number={condition_number:.1f} (>100, indicates "
            f"multicollinearity in factor matrix)"
        )

    return {
        'vif_values': vif_data,
        'condition_number': float(condition_number),
        'warnings': warnings,
        'has_severe_multicollinearity': len(severe_factors) > 0,
        'has_moderate_multicollinearity': len(moderate_factors) > 0,
        'max_vif': max(vif_data.values()) if vif_data else 0.0
    }


# ============================================================================
# SECTION 6: FACTOR CORRELATION ANALYSIS
# ============================================================================

def analyze_factor_correlations(
    factor_returns: pd.DataFrame,
    high_correlation_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Analyze correlations between factor returns.

    Highly correlated factors can cause:
    - Multicollinearity (inflated VIF)
    - Redundant risk measurements
    - Difficulty interpreting individual factor contributions

    Args:
        factor_returns: DataFrame with factors as columns, dates as index
        high_correlation_threshold: Threshold for flagging high correlations

    Returns:
        Dictionary with:
        - correlation_matrix: Full correlation matrix as dict
        - high_correlations: List of factor pairs with |corr| > threshold
        - avg_abs_correlation: Average absolute correlation
        - warnings: List of correlation warnings
        - num_high_correlations: Count of high correlations

    Example:
        >>> df = pd.DataFrame({'Market': [...], 'Value': [...]})
        >>> result = analyze_factor_correlations(df)
        >>> print(result['num_high_correlations'])
    """
    # Calculate correlation matrix
    correlation_matrix = factor_returns.corr()

    # Find high correlations
    high_correlations = []
    warnings = []

    for i in range(len(correlation_matrix.columns)):
        for j in range(i + 1, len(correlation_matrix.columns)):
            factor1 = correlation_matrix.columns[i]
            factor2 = correlation_matrix.columns[j]
            corr = correlation_matrix.iloc[i, j]

            if abs(corr) > high_correlation_threshold:
                high_correlations.append({
                    'factor1': factor1,
                    'factor2': factor2,
                    'correlation': float(corr)
                })

                warnings.append(
                    f"{factor1} and {factor2} are highly correlated "
                    f"(r={corr:.3f}). This may cause multicollinearity."
                )

    # Calculate average absolute correlation (excluding diagonal of 1.0)
    n = len(correlation_matrix)
    total_corr = 0.0
    count = 0

    for i in range(n):
        for j in range(i + 1, n):
            total_corr += abs(correlation_matrix.iloc[i, j])
            count += 1

    avg_abs_correlation = total_corr / count if count > 0 else 0.0

    return {
        'correlation_matrix': correlation_matrix.to_dict(),
        'high_correlations': high_correlations,
        'avg_abs_correlation': float(avg_abs_correlation),
        'warnings': warnings,
        'num_high_correlations': len(high_correlations)
    }


# ============================================================================
# SECTION 7: PORTFOLIO CONTEXT (Phase 3)
# ============================================================================

@dataclass
class PortfolioContext:
    """
    Pre-loaded portfolio context to avoid duplicate database queries.

    This object caches all necessary data for factor calculations,
    reducing database round-trips from ~7 to ~3 per calculation.

    Attributes:
        portfolio_id: UUID of portfolio
        portfolio: Portfolio model instance
        positions: All positions (active and inactive)
        factor_definitions: All active factor definitions
        factor_name_to_id: Mapping of factor names to UUIDs
        calculation_date: Date of calculation
    """
    portfolio_id: UUID
    portfolio: Any  # Portfolio model
    positions: List[Any]  # List of Position models
    factor_definitions: List[Any]  # List of FactorDefinition models
    factor_name_to_id: Dict[str, UUID]
    calculation_date: date

    # Cached properties (computed once, then reused)
    _active_positions: Optional[List[Any]] = field(default=None, init=False, repr=False)
    _public_positions: Optional[List[Any]] = field(default=None, init=False, repr=False)

    @property
    def equity_balance(self) -> Decimal:
        """Portfolio equity balance for weighting calculations"""
        return self.portfolio.equity_balance

    @property
    def active_positions(self) -> List[Any]:
        """All active positions (excluding exited)"""
        if self._active_positions is None:
            self._active_positions = [
                p for p in self.positions
                if p.exit_date is None
            ]
        return self._active_positions

    @property
    def public_positions(self) -> List[Any]:
        """
        Active positions excluding PRIVATE investment class.
        These are the positions used for factor analysis.
        """
        if self._public_positions is None:
            self._public_positions = [
                p for p in self.active_positions
                if p.investment_class != 'PRIVATE' or p.investment_class is None
            ]
        return self._public_positions

    def get_position_count_summary(self) -> Dict[str, int]:
        """
        Get position counts for logging/diagnostics.

        Returns:
            Dictionary with counts for total, active, public, private, exited
        """
        return {
            'total': len(self.positions),
            'active': len(self.active_positions),
            'public': len(self.public_positions),
            'private': len([p for p in self.active_positions
                           if p.investment_class == 'PRIVATE']),
            'exited': len([p for p in self.positions
                          if p.exit_date is not None])
        }


async def load_portfolio_context(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> PortfolioContext:
    """
    Load all portfolio data needed for factor calculations in one batch.

    This function performs 3 database queries:
    1. Portfolio (for equity_balance)
    2. All positions (active and inactive)
    3. Factor definitions

    This replaces ~7 duplicate queries in the original implementation,
    improving performance by ~62%.

    Args:
        db: Database session
        portfolio_id: Portfolio to load
        calculation_date: Date of calculation (for logging)

    Returns:
        PortfolioContext with all pre-loaded data

    Raises:
        ValueError: If portfolio not found or equity_balance invalid
    """
    from app.models.users import Portfolio
    from app.models.positions import Position
    from app.models.market_data import FactorDefinition

    # Query 1: Load portfolio
    portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolio = portfolio_result.scalar_one_or_none()

    if portfolio is None:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # Validate equity_balance
    if not portfolio.equity_balance or portfolio.equity_balance <= 0:
        raise ValueError(
            f"Portfolio {portfolio_id} has invalid equity_balance: {portfolio.equity_balance}. "
            "Equity-based factor calculation requires valid equity_balance."
        )

    # Query 2: Load all positions (we'll filter in properties)
    positions_stmt = select(Position).where(
        Position.portfolio_id == portfolio_id
    )
    positions_result = await db.execute(positions_stmt)
    positions = list(positions_result.scalars().all())

    # Query 3: Load factor definitions
    factor_stmt = select(FactorDefinition).where(
        FactorDefinition.is_active == True
    )
    factor_result = await db.execute(factor_stmt)
    factor_definitions = list(factor_result.scalars().all())

    # Build factor name mapping
    factor_name_to_id = {fd.name: fd.id for fd in factor_definitions}

    # Create context
    context = PortfolioContext(
        portfolio_id=portfolio_id,
        portfolio=portfolio,
        positions=positions,
        factor_definitions=factor_definitions,
        factor_name_to_id=factor_name_to_id,
        calculation_date=calculation_date
    )

    # Log summary
    counts = context.get_position_count_summary()
    logger.info(
        f"Loaded portfolio context: {counts['active']} active positions "
        f"({counts['public']} public, {counts['private']} private), "
        f"equity=${float(context.equity_balance):,.2f}"
    )

    return context


# ============================================================================
# SECTION 8: POSITION-FIRST FACTOR CALCULATION INFRASTRUCTURE
# ============================================================================
# This section provides shared utilities for position-first factor calculations.
# The pattern is:
#   1. Calculate factors per-position (once per unique symbol)
#   2. Cache position-level results in database
#   3. Load cached results for portfolio aggregation
#
# This avoids recalculating the same position factors for positions that
# appear in multiple portfolios.

async def bulk_load_cached_position_factors(
    db: AsyncSession,
    position_ids: List[UUID],
    calculation_method: str,
    calculation_date: date,
    expected_factor_count: int
) -> Dict[UUID, Dict[str, float]]:
    """
    Bulk load cached position factor betas from PositionFactorExposure table.

    This function loads all cached factor betas for the given positions in a
    single database query, avoiding N+1 query problems.

    IMPORTANT: Uses calculation_method (not factor_type) to distinguish between
    factor types because both Ridge and Spread factors have factor_type='style'.

    Args:
        db: Database session
        position_ids: List of position UUIDs to load
        calculation_method: Filter by calculation method:
                           - 'ridge_regression' for Ridge factors (6 factors)
                           - 'spread_regression' for Spread factors (4 factors)
        calculation_date: Date of calculation
        expected_factor_count: Number of factors expected per position
                              Only returns positions with ALL expected factors cached.

    Returns:
        Dictionary mapping position_id -> {factor_name: beta_value}
        Only includes positions that have ALL expected factors cached.

    Example:
        >>> cached = await bulk_load_cached_position_factors(
        ...     db, position_ids, 'ridge_regression', date.today(), 6
        ... )
        >>> # cached = {pos_id_1: {'Value': 0.5, 'Growth': 0.8, ...}, ...}
    """
    from app.models.market_data import PositionFactorExposure, FactorDefinition
    from sqlalchemy import func as sql_func

    if not position_ids:
        return {}

    # First, find positions that have ALL expected factors
    # Filter by calculation_method (not factor_type) because both Ridge and Spread
    # factors have factor_type='style' in the database
    count_stmt = (
        select(
            PositionFactorExposure.position_id,
            sql_func.count(PositionFactorExposure.factor_id).label('factor_count')
        )
        .join(FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id)
        .where(
            and_(
                PositionFactorExposure.position_id.in_(position_ids),
                PositionFactorExposure.calculation_date == calculation_date,
                FactorDefinition.calculation_method == calculation_method
            )
        )
        .group_by(PositionFactorExposure.position_id)
        .having(sql_func.count(PositionFactorExposure.factor_id) >= expected_factor_count)
    )
    count_result = await db.execute(count_stmt)
    complete_position_ids = {row[0] for row in count_result.all()}

    if not complete_position_ids:
        logger.debug(f"No positions with complete {calculation_method} cache for {calculation_date}")
        return {}

    # Now load the actual factor values for complete positions
    load_stmt = (
        select(
            PositionFactorExposure.position_id,
            FactorDefinition.name,
            PositionFactorExposure.exposure_value
        )
        .join(FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id)
        .where(
            and_(
                PositionFactorExposure.position_id.in_(complete_position_ids),
                PositionFactorExposure.calculation_date == calculation_date,
                FactorDefinition.calculation_method == calculation_method
            )
        )
    )
    load_result = await db.execute(load_stmt)

    # Build result dictionary
    cached_betas: Dict[UUID, Dict[str, float]] = {}
    for position_id, factor_name, exposure_value in load_result.all():
        if position_id not in cached_betas:
            cached_betas[position_id] = {}
        cached_betas[position_id][factor_name] = float(exposure_value)

    logger.info(
        f"Loaded {len(cached_betas)} positions with complete {calculation_method} cache "
        f"({expected_factor_count} factors each) for {calculation_date}"
    )

    return cached_betas


async def persist_position_factor_betas(
    db: AsyncSession,
    position_id: UUID,
    factor_betas: Dict[str, float],
    calculation_date: date,
    factor_name_to_id: Dict[str, UUID],
    quality_flag: str = 'full_history'
) -> Dict[str, Any]:
    """
    Persist factor betas for a single position to PositionFactorExposure table.

    This function uses upsert logic: deletes existing records for these specific
    factors, then inserts new ones. This handles re-runs without duplicating data.

    IMPORTANT: This function does NOT commit. The caller must manage transaction
    boundaries and call db.commit() when appropriate.

    Args:
        db: Database session
        position_id: Position UUID
        factor_betas: Dictionary of {factor_name: beta_value}
        calculation_date: Date of calculation
        factor_name_to_id: Mapping of factor names to UUIDs
        quality_flag: Data quality indicator

    Returns:
        Dictionary with storage results:
        - position_id: str
        - records_stored: int
        - factors_stored: List[str]
        - errors: List[str]
    """
    from app.models.market_data import PositionFactorExposure
    from sqlalchemy import delete
    import uuid

    results = {
        'position_id': str(position_id),
        'records_stored': 0,
        'factors_stored': [],
        'errors': []
    }

    try:
        # Determine which factor IDs we're storing
        factor_ids_to_store = []
        for fn in factor_betas.keys():
            mapped_name = normalize_factor_name(fn)
            if mapped_name in factor_name_to_id:
                factor_ids_to_store.append(factor_name_to_id[mapped_name])

        # Delete existing records for these specific factors (upsert pattern)
        if factor_ids_to_store:
            delete_stmt = delete(PositionFactorExposure).where(
                and_(
                    PositionFactorExposure.position_id == position_id,
                    PositionFactorExposure.calculation_date == calculation_date,
                    PositionFactorExposure.factor_id.in_(factor_ids_to_store)
                )
            )
            await db.execute(delete_stmt)

        # Insert new records
        for factor_name, beta_value in factor_betas.items():
            mapped_name = normalize_factor_name(factor_name)

            if mapped_name not in factor_name_to_id:
                results['errors'].append(f"Factor '{mapped_name}' not found in database")
                continue

            factor_id = factor_name_to_id[mapped_name]

            exposure_record = PositionFactorExposure(
                id=uuid.uuid4(),
                position_id=position_id,
                factor_id=factor_id,
                calculation_date=calculation_date,
                exposure_value=Decimal(str(beta_value)),
                quality_flag=quality_flag
            )
            db.add(exposure_record)

            results['records_stored'] += 1
            results['factors_stored'].append(mapped_name)

        logger.debug(
            f"Staged {results['records_stored']} factor betas for position {position_id}"
        )

    except Exception as e:
        logger.error(f"Error persisting factor betas for position {position_id}: {e}")
        results['errors'].append(str(e))
        raise

    return results


def calculate_position_weights(
    positions: List[Any],
    portfolio_equity: float
) -> Dict[UUID, float]:
    """
    Calculate position weights for portfolio beta aggregation.

    Weight = signed_market_value / portfolio_equity

    For leveraged portfolios, weights will sum to leverage ratio (not 1.0).
    Short positions have negative weights.

    Args:
        positions: List of Position model instances
        portfolio_equity: Portfolio equity balance

    Returns:
        Dictionary mapping position_id -> weight (can be negative for shorts)
    """
    from app.calculations.market_data import get_position_value

    weights = {}

    for position in positions:
        # Signed market value (negative for shorts)
        signed_value = float(get_position_value(position, signed=True, recalculate=False))
        weights[position.id] = signed_value / portfolio_equity

    return weights


def aggregate_position_betas_to_portfolio(
    position_betas: Dict[UUID, Dict[str, float]],
    position_weights: Dict[UUID, float]
) -> Dict[str, float]:
    """
    Aggregate position-level factor betas to portfolio level using provided weights.

    Portfolio Beta = Σ(weight_i × beta_i)

    Args:
        position_betas: Dictionary mapping position_id -> {factor_name: beta}
        position_weights: Dictionary mapping position_id -> weight (signed, based on equity)

    Returns:
        Dictionary of portfolio-level factor betas {factor_name: beta}

    Example:
        >>> pos_betas = {
        ...     uuid1: {'Value': 0.8, 'Growth': 1.2},
        ...     uuid2: {'Value': 0.5, 'Growth': 0.9}
        ... }
        >>> weights = {uuid1: 0.6, uuid2: 0.4}  # Weights based on signed_exposure / equity
        >>> portfolio_betas = aggregate_position_betas_to_portfolio(pos_betas, weights)
        >>> # portfolio_betas = {'Value': 0.68, 'Growth': 1.08}
    """
    # Collect all factor names
    factor_names = set()
    for betas in position_betas.values():
        factor_names.update(betas.keys())

    # Calculate weighted average for each factor
    portfolio_betas = {}

    for factor_name in factor_names:
        weighted_sum = 0.0

        for position_id, weight in position_weights.items():
            if position_id in position_betas and factor_name in position_betas[position_id]:
                weighted_sum += position_betas[position_id][factor_name] * weight

        portfolio_betas[factor_name] = weighted_sum

    return portfolio_betas
