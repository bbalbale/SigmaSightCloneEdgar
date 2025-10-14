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
# SECTION 3: MARKET VALUE UTILITIES
# ============================================================================

def _is_options_position(position) -> bool:
    """
    Check if position is an options position.

    Args:
        position: Position object

    Returns:
        True if position type is LC, LP, SC, or SP
    """
    from app.models.positions import PositionType
    return position.position_type in [
        PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP
    ]


def get_position_market_value(
    position,
    use_stored: bool = True,
    recalculate: bool = False
) -> Decimal:
    """
    Get position market value with consistent logic.

    This provides a single source of truth for market value calculation,
    eliminating inconsistencies between functions.

    Args:
        position: Position object
        use_stored: If True and position.market_value exists, use it
        recalculate: If True, always recalculate (ignores use_stored)

    Returns:
        Market value as Decimal

    Note:
        Recalculated value = |quantity × price × multiplier|
        where multiplier = 100 for options, 1 for others
    """
    if not recalculate and use_stored and position.market_value:
        return Decimal(str(position.market_value))

    # Recalculate
    multiplier = OPTIONS_MULTIPLIER if _is_options_position(position) else 1
    price = position.last_price or position.entry_price

    if price is None:
        return Decimal('0')

    return abs(Decimal(str(position.quantity)) * Decimal(str(price)) * multiplier)


def get_position_signed_exposure(position) -> Decimal:
    """
    Get signed exposure (negative for shorts, positive for longs).

    This is used for portfolio aggregation where direction matters.

    Args:
        position: Position object

    Returns:
        Positive for LONG/LC/LP, negative for SHORT/SC/SP
    """
    from app.models.positions import PositionType

    market_value = get_position_market_value(position)

    # Apply sign based on position type
    if position.position_type in [PositionType.SHORT, PositionType.SC, PositionType.SP]:
        return -market_value
    return market_value


def get_position_magnitude_exposure(position) -> Decimal:
    """
    Get absolute magnitude exposure (always positive).

    This is used for gross exposure calculations.

    Args:
        position: Position object

    Returns:
        Absolute value of market value
    """
    return abs(get_position_market_value(position))


# ============================================================================
# SECTION 4: STATISTICAL CLASSIFICATION
# ============================================================================

# R² thresholds
R_SQUARED_THRESHOLDS = {
    'excellent': 0.70,
    'good': 0.50,
    'fair': 0.30,
    'poor': 0.10
}

# Significance thresholds
SIGNIFICANCE_THRESHOLD_STRICT = 0.05  # 95% confidence
SIGNIFICANCE_THRESHOLD_RELAXED = 0.10  # 90% confidence


def classify_r_squared(r_squared: float) -> Dict[str, Any]:
    """
    Classify R² (goodness of fit) for factor model.

    R² measures how much of position return variance is explained
    by the factor model. Low R² indicates high idiosyncratic risk.

    Args:
        r_squared: R² value from regression (0 to 1)

    Returns:
        Dictionary with:
        - quality: str ('excellent', 'good', 'fair', 'poor', 'very_poor')
        - interpretation: str
        - variance_explained_pct: float (R² as percentage)
        - idiosyncratic_risk_pct: float (100 - R²)
        - r_squared: float (original value)

    Example:
        >>> classify_r_squared(0.42)
        {'quality': 'fair', 'variance_explained_pct': 42.0, ...}
    """
    if r_squared >= R_SQUARED_THRESHOLDS['excellent']:
        quality = 'excellent'
        interpretation = 'Factor model explains most variance'
    elif r_squared >= R_SQUARED_THRESHOLDS['good']:
        quality = 'good'
        interpretation = 'Factor model explains variance well'
    elif r_squared >= R_SQUARED_THRESHOLDS['fair']:
        quality = 'fair'
        interpretation = 'Moderate factor explanation, some idiosyncratic risk'
    elif r_squared >= R_SQUARED_THRESHOLDS['poor']:
        quality = 'poor'
        interpretation = 'High idiosyncratic risk, factor model limited'
    else:
        quality = 'very_poor'
        interpretation = 'Very high idiosyncratic risk, factor model inadequate'

    return {
        'quality': quality,
        'interpretation': interpretation,
        'variance_explained_pct': round(r_squared * 100, 1),
        'idiosyncratic_risk_pct': round((1 - r_squared) * 100, 1),
        'r_squared': r_squared
    }


def classify_significance(p_value: float, strict: bool = False) -> Dict[str, Any]:
    """
    Classify statistical significance of a regression coefficient.

    Non-significant betas (high p-values) are unreliable and shouldn't
    be trusted for portfolio decisions (AQR best practice).

    Args:
        p_value: P-value from regression
        strict: If True, use 0.05 threshold; if False, use 0.10

    Returns:
        Dictionary with:
        - is_significant: bool
        - confidence_level: str ('***', '**', '*', 'ns')
        - interpretation: str (human-readable)
        - p_value: float
        - threshold: float

    Example:
        >>> classify_significance(0.08)
        {'is_significant': True, 'confidence_level': '*', ...}
    """
    threshold = SIGNIFICANCE_THRESHOLD_STRICT if strict else SIGNIFICANCE_THRESHOLD_RELAXED

    if p_value < 0.01:
        level = '***'
        interpretation = 'highly significant (p < 0.01)'
    elif p_value < 0.05:
        level = '**'
        interpretation = 'significant (p < 0.05)'
    elif p_value < 0.10:
        level = '*'
        interpretation = 'marginally significant (p < 0.10)'
    else:
        level = 'ns'
        interpretation = 'not significant (p ≥ 0.10)'

    return {
        'is_significant': p_value < threshold,
        'confidence_level': level,
        'interpretation': interpretation,
        'p_value': p_value,
        'threshold': threshold
    }


# ============================================================================
# SECTION 5: MULTICOLLINEARITY DIAGNOSTICS
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
