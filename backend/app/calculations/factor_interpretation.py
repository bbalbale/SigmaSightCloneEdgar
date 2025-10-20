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
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "heavily concentrated in growth stocks"
                risk_note = " Consider hedging with value positions (VTV) or reducing tech/growth exposure."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "tilted toward growth stocks"
                risk_note = ""
            else:
                intensity = "slightly favors growth stocks"
                risk_note = ""

            explanation = (
                f"{magnitude} growth tilt. Portfolio {intensity}, "
                f"gaining {abs_beta:.2f}% when growth outperforms value by 1%. "
                f"Vulnerable to growth-to-value rotation.{risk_note}"
            )
        elif beta < 0:
            direction = "Value"
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "heavily concentrated in value stocks"
                risk_note = " Well-positioned for value cycles, but may underperform in growth rallies."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "tilted toward value stocks"
                risk_note = ""
            else:
                intensity = "slightly favors value stocks"
                risk_note = ""

            explanation = (
                f"{magnitude} value tilt. Portfolio {intensity}, "
                f"gaining {abs_beta:.2f}% when value outperforms growth by 1%. "
                f"Benefits from value rotation.{risk_note}"
            )
        else:
            direction = "Balanced"
            explanation = "Balanced growth-value exposure with minimal style bias."

    elif factor_name == "Momentum Spread":
        if beta > 0:
            direction = "Momentum"
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "strongly follows trending stocks"
                risk_note = " High momentum risk - vulnerable to sudden trend reversals."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "moderately exposed to trending stocks"
                risk_note = ""
            else:
                intensity = "slightly follows trending stocks"
                risk_note = ""

            explanation = (
                f"{magnitude} momentum exposure. Portfolio {intensity}, "
                f"gaining {abs_beta:.2f}% when momentum outperforms the market by 1%. "
                f"Risk of reversal when trends break.{risk_note}"
            )
        elif beta < 0:
            direction = "Contrarian"
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "strongly positioned against momentum"
                risk_note = " May significantly lag during strong uptrends."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "moderately contrarian"
                risk_note = ""
            else:
                intensity = "slightly contrarian"
                risk_note = ""

            explanation = (
                f"{magnitude} contrarian tilt. Portfolio {intensity}, "
                f"gaining {abs_beta:.2f}% when the market outperforms momentum by 1%. "
                f"May lag during strong trends.{risk_note}"
            )
        else:
            direction = "Neutral"
            explanation = "Neutral momentum exposure, neither chasing nor fading trends."

    elif factor_name == "Size Spread":
        if beta > 0:
            direction = "Small Cap"
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "heavily concentrated in small cap stocks"
                risk_note = " Significant small cap exposure increases portfolio volatility."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "tilted toward small cap stocks"
                risk_note = ""
            else:
                intensity = "slightly favors small cap stocks"
                risk_note = ""

            explanation = (
                f"{magnitude} small cap tilt. Portfolio {intensity}, "
                f"gaining {abs_beta:.2f}% when small caps outperform large caps by 1%. "
                f"Higher volatility and liquidity risk.{risk_note}"
            )
        elif beta < 0:
            direction = "Large Cap"
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "heavily concentrated in mega-cap stocks"
                risk_note = " May miss small cap premium opportunities."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "tilted toward large cap stocks"
                risk_note = ""
            else:
                intensity = "slightly favors large cap stocks"
                risk_note = ""

            explanation = (
                f"{magnitude} large cap tilt. Portfolio {intensity}, "
                f"gaining {abs_beta:.2f}% when large caps outperform small caps by 1%. "
                f"Lower volatility.{risk_note}"
            )
        else:
            direction = "Balanced"
            explanation = "Balanced size exposure across market capitalizations."

    elif factor_name == "Quality Spread":
        if beta > 0:
            direction = "Quality"
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "heavily concentrated in high-quality companies"
                risk_note = " Strong quality bias provides downside protection but may lag in risk-on rallies."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "tilted toward high-quality companies"
                risk_note = ""
            else:
                intensity = "slightly favors high-quality companies"
                risk_note = ""

            explanation = (
                f"{magnitude} quality tilt. Portfolio {intensity} with strong fundamentals, "
                f"gaining {abs_beta:.2f}% when quality outperforms the market by 1%. "
                f"Defensive positioning for downturns.{risk_note}"
            )
        elif beta < 0:
            direction = "Speculative"
            # Adjust language intensity based on magnitude
            if abs_beta > SPREAD_BETA_THRESHOLDS['strong']:
                intensity = "heavily concentrated in higher-risk stocks"
                risk_note = " Elevated risk from speculative positions."
            elif abs_beta > SPREAD_BETA_THRESHOLDS['moderate']:
                intensity = "tilted toward higher-risk stocks"
                risk_note = ""
            else:
                intensity = "slightly favors higher-risk stocks"
                risk_note = ""

            explanation = (
                f"{magnitude} speculative tilt. Portfolio {intensity}, "
                f"gaining {abs_beta:.2f}% when speculative stocks outperform quality by 1%. "
                f"Higher volatility.{risk_note}"
            )
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
