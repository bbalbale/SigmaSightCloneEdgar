"""
Factor Interpretation Utilities
Converts spread factor betas to user-friendly explanations.

This module provides plain English interpretations of spread factor betas,
making complex financial metrics accessible to both retail and institutional investors.

Created: 2025-10-20
"""
from typing import Dict
from app.constants.factors import SPREAD_BETA_THRESHOLDS


def interpret_spread_beta(factor_name: str, beta: float) -> Dict[str, str]:
    """
    Convert spread beta to user-friendly explanation.

    Takes a numerical beta and generates:
    - Magnitude classification (Strong, Moderate, Weak)
    - Direction (Growth, Value, Momentum, etc.)
    - Plain English explanation with context
    - Risk level assessment (high, medium, low)

    Args:
        factor_name: Name of the spread factor (e.g., "Growth-Value Spread")
        beta: Beta coefficient from OLS regression

    Returns:
        Dict with:
        - magnitude: 'Strong', 'Moderate', or 'Weak'
        - direction: Factor-specific direction (e.g., 'Growth', 'Value')
        - explanation: Plain English description with percentages
        - risk_level: 'high', 'medium', or 'low'

    Example:
        interpret_spread_beta("Growth-Value Spread", 0.85)
        → {
            'magnitude': 'Strong',
            'direction': 'Growth',
            'explanation': 'Strong growth tilt. Portfolio gains 0.85% when...',
            'risk_level': 'high'
        }
    """
    # Determine magnitude and risk level based on absolute beta value
    abs_beta = abs(beta)

    if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
        magnitude = "Strong"
        risk_level = "high"
    elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
        magnitude = "Moderate"
        risk_level = "medium"
    else:
        magnitude = "Weak"
        risk_level = "low"

    # Generate factor-specific interpretations
    if factor_name == "Growth-Value Spread":
        if beta > 0:
            direction = "Growth"
            explanation = (
                f"{magnitude} growth tilt. Portfolio gains {abs_beta:.2f}% when "
                f"growth stocks outperform value by 1%. Vulnerable to growth-to-value rotation."
            )
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                explanation += " Consider hedging with value positions (VTV) or reducing tech/growth exposure."
        elif beta < 0:
            direction = "Value"
            explanation = (
                f"{magnitude} value tilt. Portfolio gains {abs_beta:.2f}% when "
                f"value stocks outperform growth by 1%. Benefits from value rotation."
            )
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                explanation += " Well-positioned for value cycles, but may underperform in growth rallies."
        else:
            direction = "Balanced"
            explanation = "Balanced growth-value exposure with minimal style bias."

    elif factor_name == "Momentum Spread":
        if beta > 0:
            direction = "Momentum"
            explanation = (
                f"{magnitude} momentum exposure. Portfolio follows trending stocks, "
                f"gaining {abs_beta:.2f}% when momentum outperforms by 1%. Risk of reversal when trends break."
            )
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                explanation += " High momentum risk - vulnerable to sudden trend reversals."
        elif beta < 0:
            direction = "Contrarian"
            explanation = (
                f"{magnitude} contrarian tilt. Portfolio benefits when momentum reverses, "
                f"gaining {abs_beta:.2f}% when momentum underperforms by 1%. May lag during strong trends."
            )
        else:
            direction = "Neutral"
            explanation = "Neutral momentum exposure, neither chasing nor fading trends."

    elif factor_name == "Size Spread":
        if beta > 0:
            direction = "Small Cap"
            explanation = (
                f"{magnitude} small cap tilt. Portfolio gains {abs_beta:.2f}% when "
                f"small caps outperform large caps by 1%. Higher volatility and liquidity risk."
            )
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                explanation += " Significant small cap exposure increases portfolio volatility."
        elif beta < 0:
            direction = "Large Cap"
            explanation = (
                f"{magnitude} large cap tilt. Portfolio favors mega-cap stocks, "
                f"gaining {abs_beta:.2f}% when large caps outperform by 1%. Lower volatility, may miss small cap premiums."
            )
        else:
            direction = "Balanced"
            explanation = "Balanced size exposure across market capitalizations."

    elif factor_name == "Quality Spread":
        if beta > 0:
            direction = "Quality"
            explanation = (
                f"{magnitude} quality tilt. Portfolio favors high-quality companies with strong fundamentals, "
                f"gaining {abs_beta:.2f}% when quality outperforms by 1%. Defensive positioning for downturns."
            )
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                explanation += " Strong quality bias provides downside protection but may lag in risk-on rallies."
        elif beta < 0:
            direction = "Speculative"
            explanation = (
                f"{magnitude} speculative tilt. Portfolio favors higher-risk stocks, "
                f"gaining {abs_beta:.2f}% when speculative stocks outperform quality by 1%. Higher volatility."
            )
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                explanation += " Elevated risk from speculative positions."
        else:
            direction = "Balanced"
            explanation = "Balanced quality exposure, mix of stable and growth-oriented companies."

    else:
        # Fallback for unknown factor names
        direction = "Unknown"
        explanation = f"Beta: {beta:.2f}"
        risk_level = "medium"

    return {
        'magnitude': magnitude,
        'direction': direction,
        'explanation': explanation,
        'risk_level': risk_level
    }


def generate_portfolio_summary(spread_factors: list) -> str:
    """
    Generate plain English summary of portfolio style tilts from spread factors.

    Identifies dominant tilts and creates a concise portfolio characterization.

    Args:
        spread_factors: List of dicts with 'direction' and 'magnitude' fields

    Returns:
        String summarizing overall portfolio tilts

    Examples:
        [{'direction': 'Growth', 'magnitude': 'Strong'}]
        → "Portfolio shows strong growth tilt."

        [{'direction': 'Growth', 'magnitude': 'Strong'},
         {'direction': 'Momentum', 'magnitude': 'Moderate'}]
        → "Portfolio shows strong growth tilt with moderate momentum exposure."
    """
    # Extract strong factors
    strong_factors = [
        sf['direction']
        for sf in spread_factors
        if sf.get('magnitude') == 'Strong' and sf['direction'] not in ['Balanced', 'Neutral', 'Unknown']
    ]

    # Extract moderate factors
    moderate_factors = [
        sf['direction']
        for sf in spread_factors
        if sf.get('magnitude') == 'Moderate' and sf['direction'] not in ['Balanced', 'Neutral', 'Unknown']
    ]

    # Build summary
    if len(strong_factors) == 0 and len(moderate_factors) == 0:
        return "Portfolio shows balanced exposure across style factors with no dominant tilts."

    if len(strong_factors) == 1 and len(moderate_factors) == 0:
        return f"Portfolio shows strong {strong_factors[0].lower()} tilt."

    if len(strong_factors) == 2:
        return f"Portfolio shows strong {strong_factors[0].lower()} and {strong_factors[1].lower()} tilts."

    if len(strong_factors) >= 3:
        factors_text = ', '.join(strong_factors[:-1]) + f', and {strong_factors[-1]}'
        return f"Portfolio shows strong tilts toward {factors_text.lower()}."

    if len(strong_factors) == 1 and len(moderate_factors) >= 1:
        return (
            f"Portfolio shows strong {strong_factors[0].lower()} tilt "
            f"with moderate {moderate_factors[0].lower()} exposure."
        )

    if len(strong_factors) == 0 and len(moderate_factors) == 1:
        return f"Portfolio shows moderate {moderate_factors[0].lower()} tilt."

    if len(strong_factors) == 0 and len(moderate_factors) >= 2:
        factors_text = ' and '.join(moderate_factors[:2])
        return f"Portfolio shows moderate {factors_text.lower()} tilts."

    # Fallback
    return "Portfolio has mixed style exposures."
