"""
Shared Regression Utilities for Factor Analysis
Provides standardized OLS regression, statistical classification, and diagnostics

Created: 2025-10-20 (Calculation Consolidation Refactor)
Purpose: DRY up regression logic across market_beta, interest_rate_beta, and factor calculations

This module consolidates duplicate regression scaffolding from:
- market_beta.py (OLS vs SPY)
- interest_rate_beta.py (OLS vs TLT)
- factors_spread.py (OLS vs spread factors)
"""
from typing import Dict, Any, Optional
import numpy as np
import statsmodels.api as sm

from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# SECTION 1: OLS REGRESSION WRAPPER
# ============================================================================

def run_single_factor_regression(
    y: np.ndarray,
    x: np.ndarray,
    cap: Optional[float] = None,
    confidence: float = 0.10,
    return_diagnostics: bool = True
) -> Dict[str, Any]:
    """
    Run OLS regression with standardized output and optional beta capping.

    Regression model: y = α + β×x + ε

    This function provides a single source of truth for all single-factor
    regressions (market beta, IR beta, spread beta, etc.), ensuring:
    - Consistent beta capping logic
    - Standardized significance testing
    - Uniform error handling
    - Normalized output format

    Args:
        y: Dependent variable (position returns)
        x: Independent variable (factor returns)
        cap: Optional beta cap limit (e.g., 5.0 caps beta at ±5.0)
        confidence: Confidence level for significance (0.05 = 95%, 0.10 = 90%)
        return_diagnostics: If True, include std_error, p_value in output

    Returns:
        Dictionary with:
        - beta: float (slope coefficient, potentially capped)
        - alpha: float (intercept)
        - r_squared: float (goodness of fit, 0 to 1)
        - success: bool (True if regression completed)
        - capped: bool (True if beta was capped)
        - original_beta: float (original beta before capping, if capped)
        - observations: int (number of data points)

        If return_diagnostics=True, also includes:
        - std_error: float (standard error of beta)
        - p_value: float (significance of beta)
        - is_significant: bool (p_value < confidence threshold)

    Raises:
        ValueError: If arrays have different lengths, contain NaN, or insufficient data

    Example:
        >>> import numpy as np
        >>> market_returns = np.array([0.01, -0.02, 0.015, 0.03, -0.01])
        >>> stock_returns = np.array([0.012, -0.025, 0.018, 0.036, -0.012])
        >>> result = run_single_factor_regression(stock_returns, market_returns, cap=5.0)
        >>> print(f"Beta: {result['beta']:.3f}, R²: {result['r_squared']:.3f}")
    """
    # Validation
    if len(y) != len(x):
        raise ValueError(f"Array length mismatch: y has {len(y)} elements, x has {len(x)} elements")

    if np.any(np.isnan(y)) or np.any(np.isnan(x)):
        raise ValueError("Arrays contain NaN values. Clean data before regression.")

    if len(y) < 2:
        raise ValueError(f"Insufficient data points: {len(y)} (minimum: 2)")

    try:
        # Add constant term for intercept
        X_with_const = sm.add_constant(x)

        # Run OLS regression
        model = sm.OLS(y, X_with_const).fit()

        # Extract coefficients
        alpha = float(model.params[0])  # Intercept
        beta_raw = float(model.params[1])  # Slope coefficient
        r_squared = float(model.rsquared)

        # Apply beta capping if requested
        capped = False
        original_beta = beta_raw

        if cap is not None:
            if abs(beta_raw) > cap:
                capped = True
                original_beta = beta_raw
                beta = max(-cap, min(cap, beta_raw))

                logger.debug(
                    f"Beta capped: {original_beta:.4f} → {beta:.4f} (cap={cap})"
                )
            else:
                beta = beta_raw
        else:
            beta = beta_raw

        # Build result dictionary
        result = {
            'beta': beta,
            'alpha': alpha,
            'r_squared': r_squared,
            'success': True,
            'capped': capped,
            'observations': len(y)
        }

        if capped:
            result['original_beta'] = original_beta

        # Add diagnostic information if requested
        if return_diagnostics:
            std_error = float(model.bse[1])  # Standard error of beta
            p_value = float(model.pvalues[1])  # P-value for beta
            is_significant = p_value < confidence

            result.update({
                'std_error': std_error,
                'p_value': p_value,
                'is_significant': is_significant
            })

        return result

    except Exception as e:
        logger.error(f"Regression failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'observations': len(y)
        }


# ============================================================================
# SECTION 2: R² CLASSIFICATION
# ============================================================================

# R² thresholds (moved from factor_utils.py)
R_SQUARED_THRESHOLDS = {
    'excellent': 0.70,
    'good': 0.50,
    'fair': 0.30,
    'poor': 0.10
}


def classify_r_squared(r_squared: float) -> Dict[str, Any]:
    """
    Classify R² (goodness of fit) for factor model.

    R² measures how much of position return variance is explained
    by the factor model. Low R² indicates high idiosyncratic risk.

    Classification thresholds:
    - Excellent: R² ≥ 0.70 (factor model explains most variance)
    - Good: 0.50 ≤ R² < 0.70 (factor model explains variance well)
    - Fair: 0.30 ≤ R² < 0.50 (moderate factor explanation)
    - Poor: 0.10 ≤ R² < 0.30 (high idiosyncratic risk)
    - Very Poor: R² < 0.10 (factor model inadequate)

    Args:
        r_squared: R² value from regression (0 to 1)

    Returns:
        Dictionary with:
        - quality: str ('excellent', 'good', 'fair', 'poor', 'very_poor')
        - interpretation: str (human-readable explanation)
        - variance_explained_pct: float (R² as percentage)
        - idiosyncratic_risk_pct: float (100 - R² percentage)
        - r_squared: float (original value)

    Example:
        >>> result = classify_r_squared(0.42)
        >>> print(result['quality'])  # 'fair'
        >>> print(result['variance_explained_pct'])  # 42.0
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


# ============================================================================
# SECTION 3: SIGNIFICANCE CLASSIFICATION
# ============================================================================

# Significance thresholds (moved from factor_utils.py)
SIGNIFICANCE_THRESHOLD_STRICT = 0.05  # 95% confidence
SIGNIFICANCE_THRESHOLD_RELAXED = 0.10  # 90% confidence


def classify_significance(p_value: float, strict: bool = False) -> Dict[str, Any]:
    """
    Classify statistical significance of a regression coefficient.

    Non-significant betas (high p-values) are unreliable and shouldn't
    be trusted for portfolio decisions (AQR best practice).

    Confidence levels:
    - p < 0.01: Highly significant (***)
    - p < 0.05: Significant (**)
    - p < 0.10: Marginally significant (*)
    - p ≥ 0.10: Not significant (ns)

    Args:
        p_value: P-value from regression
        strict: If True, use 0.05 threshold; if False, use 0.10

    Returns:
        Dictionary with:
        - is_significant: bool (p_value < threshold)
        - confidence_level: str ('***', '**', '*', 'ns')
        - interpretation: str (human-readable)
        - p_value: float (original value)
        - threshold: float (threshold used for classification)

    Example:
        >>> result = classify_significance(0.08, strict=False)
        >>> print(result['is_significant'])  # True (with relaxed threshold)
        >>> print(result['confidence_level'])  # '*'
    """
    threshold = SIGNIFICANCE_THRESHOLD_STRICT if strict else SIGNIFICANCE_THRESHOLD_RELAXED

    # Determine confidence level star rating
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
