"""
Spread Factor Analytics API endpoints

Endpoints for portfolio-level spread factor exposures using 180-day OLS regression.
Spread factors are long-short factors that eliminate multicollinearity:
- Growth-Value Spread (VUG - VTV)
- Momentum Spread (MTUM - SPY)
- Size Spread (IWM - SPY)
- Quality Spread (QUAL - SPY)

Created: 2025-10-20
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel
from typing import List, Optional
import time

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.schemas.auth import CurrentUser
from app.models.market_data import FactorDefinition, FactorExposure
from app.calculations.factor_interpretation import interpret_spread_beta
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/portfolio", tags=["spread-factors"])


class SpreadFactorData(BaseModel):
    """Individual spread factor data"""
    name: str
    beta: float
    exposure_dollar: Optional[float] = None
    direction: str
    magnitude: str  # Strong, Moderate, Weak
    risk_level: str  # high, medium, low
    explanation: str


class SpreadFactorsResponse(BaseModel):
    """Response model for spread factor exposures"""
    available: bool
    portfolio_id: str
    calculation_date: Optional[str] = None
    factors: List[SpreadFactorData] = []
    metadata: dict = {}


@router.get("/{portfolio_id}/spread-factors", response_model=SpreadFactorsResponse)
async def get_portfolio_spread_factors(
    portfolio_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Portfolio-level spread factor exposures with user-friendly interpretations.

    Returns 4 long-short spread factor betas calculated using 180-day OLS regression:
    - Growth-Value Spread (VUG - VTV): Growth vs Value exposure
    - Momentum Spread (MTUM - SPY): Momentum vs Market
    - Size Spread (IWM - SPY): Small Cap vs Large Cap
    - Quality Spread (QUAL - SPY): Quality vs Market

    Each factor includes:
    - Beta coefficient (180-day regression)
    - Direction (Growth/Value, Momentum/Contrarian, etc.)
    - Magnitude classification (Strong/Moderate/Weak)
    - Risk level assessment (high/medium/low)
    - Plain English explanation

    Spread factors solve the multicollinearity problem in traditional factor models
    by using long-short positions that are less correlated with the market (r~0.3 vs 0.93+).

    **Implementation Notes**:
    - Uses precomputed batch results from factor_exposures table
    - 180-day regression window for statistical robustness
    - Interpretations generated via factor_interpretation module
    - Beta thresholds: |beta| > 0.5 = strong, 0.2-0.5 = moderate, < 0.2 = weak

    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        SpreadFactorsResponse with 4 spread factors and interpretations

    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during retrieval
    """
    try:
        start = time.time()

        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        # Get active spread factors (factor_type='spread')
        spread_factors_stmt = (
            select(FactorDefinition.id, FactorDefinition.name)
            .where(and_(
                FactorDefinition.is_active == True,
                FactorDefinition.factor_type == 'spread'
            ))
            .order_by(FactorDefinition.display_order.asc())
        )
        spread_result = await db.execute(spread_factors_stmt)
        spread_rows = spread_result.all()
        spread_factor_ids = [row[0] for row in spread_rows]

        if not spread_factor_ids:
            logger.warning("No active spread factors found in database")
            return SpreadFactorsResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"error": "No spread factors defined"}
            )

        # Find latest calculation date for spread factors
        latest_date_stmt = (
            select(func.max(FactorExposure.calculation_date))
            .where(and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.factor_id.in_(spread_factor_ids)
            ))
        )
        latest_date_result = await db.execute(latest_date_stmt)
        latest_date = latest_date_result.scalar_one_or_none()

        if latest_date is None:
            logger.info(f"No spread factor calculations found for portfolio {portfolio_id}")
            return SpreadFactorsResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                metadata={"reason": "no_calculations_available"}
            )

        # Load spread factor exposures for latest date
        exposures_stmt = (
            select(FactorExposure, FactorDefinition)
            .join(FactorDefinition, FactorExposure.factor_id == FactorDefinition.id)
            .where(and_(
                FactorExposure.portfolio_id == portfolio_id,
                FactorExposure.calculation_date == latest_date,
                FactorExposure.factor_id.in_(spread_factor_ids)
            ))
        )
        exposures_result = await db.execute(exposures_stmt)
        exposure_rows = exposures_result.all()

        if not exposure_rows:
            logger.warning(f"Spread factors exist but no exposures for portfolio {portfolio_id}")
            return SpreadFactorsResponse(
                available=False,
                portfolio_id=str(portfolio_id),
                calculation_date=latest_date.isoformat(),
                metadata={"reason": "no_exposures_calculated"}
            )

        # Build response with interpretations
        factors = []
        for exposure, definition in exposure_rows:
            beta = float(exposure.exposure_value)

            # Get interpretation
            interpretation = interpret_spread_beta(definition.name, beta)

            factors.append(SpreadFactorData(
                name=definition.name,
                beta=beta,
                exposure_dollar=float(exposure.exposure_dollar) if exposure.exposure_dollar else None,
                direction=interpretation['direction'],
                magnitude=interpretation['magnitude'],
                risk_level=interpretation['risk_level'],
                explanation=interpretation['explanation']
            ))

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow spread-factors response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Spread factors retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return SpreadFactorsResponse(
            available=True,
            portfolio_id=str(portfolio_id),
            calculation_date=latest_date.isoformat(),
            factors=factors,
            metadata={
                "calculation_method": "OLS_SPREAD",
                "regression_window_days": 180,
                "factors_calculated": len(factors),
                "expected_factors": 4
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Spread factors failed for {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving spread factors"
        )
