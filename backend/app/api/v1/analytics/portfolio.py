"""
Portfolio Analytics API endpoints

Endpoints for portfolio-level analytics including overview metrics,
exposures, P&L calculations, and performance data.
"""
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
import time

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.schemas.auth import CurrentUser
from app.models.users import Portfolio
from app.schemas.analytics import (
    PortfolioOverviewResponse,
    CorrelationMatrixResponse,
    DiversificationScoreResponse,
    PortfolioFactorExposuresResponse,
    PositionFactorExposuresResponse,
    StressTestResponse,
    PortfolioRiskMetricsResponse,
)
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from app.services.correlation_service import CorrelationService
from app.services.factor_exposure_service import FactorExposureService
from app.services.stress_test_service import StressTestService
from app.services.risk_metrics_service import RiskMetricsService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio-analytics"])


@router.get("/{portfolio_id}/overview", response_model=PortfolioOverviewResponse)
async def get_portfolio_overview(
    portfolio_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive portfolio overview with exposures, P&L, and position metrics.
    
    This endpoint provides portfolio-level analytics for dashboard consumption including:
    - Total portfolio value and cash balance
    - Long/short/gross/net exposure metrics with percentages
    - P&L breakdown (total, unrealized, realized)
    - Position count breakdown by type (long, short, options)
    
    **Implementation Notes**:
    - Uses existing batch processing results where available
    - Graceful degradation for missing calculation data
    - <500ms target response time with 5-minute cache TTL
    - Portfolio ownership validation ensures data security
    
    **Frontend Integration**: 
    Required for portfolio page aggregate cards at `http://localhost:3005/portfolio`
    
    Args:
        portfolio_id: Portfolio UUID to analyze
        current_user: Authenticated user from JWT token
        db: Database session
        
    Returns:
        PortfolioOverviewResponse with complete portfolio analytics
        
    Raises:
        404: Portfolio not found or not owned by user
        500: Internal server error during calculation
    """
    try:
        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        
        # Get analytics service and calculate overview
        analytics_service = PortfolioAnalyticsService()
        overview_data = await analytics_service.get_portfolio_overview(db, portfolio_id)
        
        # Return validated response
        return PortfolioOverviewResponse(**overview_data)
        
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating portfolio overview {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error calculating portfolio analytics")


@router.get("/{portfolio_id}/correlation-matrix", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix(
    portfolio_id: UUID,
    lookback_days: int = Query(90, ge=30, le=365, description="Lookback period in days"),
    min_overlap: int = Query(30, ge=10, le=365, description="Minimum overlapping data points"),
    max_symbols: int = Query(25, ge=2, le=50, description="Maximum symbols to include in matrix"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the correlation matrix for portfolio positions.
    
    Returns pre-calculated pairwise correlations between all positions in the portfolio,
    ordered by position weight (gross market value).
    
    Args:
        portfolio_id: Portfolio UUID
        lookback_days: Duration for correlation calculation (30-365 days)
        min_overlap: Minimum data points required for valid correlation (10-365)
        
    Returns:
        CorrelationMatrixResponse with matrix data or unavailable status
    """
    # Input validation
    if min_overlap > lookback_days:
        raise HTTPException(
            status_code=400, 
            detail="Min overlap cannot exceed lookback days"
        )
    
    try:
        # Performance monitoring
        start = time.time()
        
        # Validate portfolio ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        
        # Get correlation matrix from service
        svc = CorrelationService(db)
        result = await svc.get_matrix(portfolio_id, lookback_days, min_overlap, max_symbols)
        
        # Log performance
        elapsed = time.time() - start
        if elapsed > 0.5:
            logger.warning(
                f"Slow correlation matrix response: {elapsed:.2f}s for portfolio {portfolio_id}"
            )
        else:
            logger.info(
                f"Correlation matrix retrieved in {elapsed:.3f}s for portfolio {portfolio_id}"
            )
        
        # Return appropriate response based on availability
        if "available" in result and result["available"] is False:
            return CorrelationMatrixResponse(
                available=False,
                metadata=result.get("metadata", {})
            )
        else:
            return CorrelationMatrixResponse(**result)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Correlation matrix failed for {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error computing correlation matrix"
        )


@router.get("/{portfolio_id}/diversification-score", response_model=DiversificationScoreResponse)
async def get_diversification_score(
    portfolio_id: UUID,
    lookback_days: int = Query(90, ge=30, le=365, description="Lookback period in days"),
    min_overlap: int = Query(30, ge=10, le=365, description="Minimum overlapping data points"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the weighted absolute portfolio correlation (0–1) using the full
    calculation symbol set for the latest correlation run that matches the
    requested lookback window.
    """
    if min_overlap > lookback_days:
        raise HTTPException(status_code=400, detail="Min overlap cannot exceed lookback days")

    try:
        start = time.time()

        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        svc = CorrelationService(db)
        result = await svc.get_weighted_correlation(portfolio_id, lookback_days, min_overlap)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow diversification-score response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Diversification-score retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return DiversificationScoreResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Diversification score failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error computing diversification score")


@router.get("/{portfolio_id}/factor-exposures", response_model=PortfolioFactorExposuresResponse)
async def get_portfolio_factor_exposures(
    portfolio_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Portfolio-level factor exposures for the most recent calculation date.

    Returns factor betas (and optional dollar exposures) aggregated at the
    portfolio level. Uses the latest complete set of exposures.
    """
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        svc = FactorExposureService(db)
        result = await svc.get_portfolio_exposures(portfolio_id)

        elapsed = time.time() - start
        if elapsed > 0.2:
            logger.warning(f"Slow factor-exposures response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Factor-exposures retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return PortfolioFactorExposuresResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Factor exposures failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving factor exposures")


@router.get("/{portfolio_id}/positions/factor-exposures", response_model=PositionFactorExposuresResponse)
async def list_position_factor_exposures(
    portfolio_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Number of positions to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    symbols: str | None = Query(None, description="Optional CSV list of symbols to filter"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Position-level factor exposures for the most recent calculation date.

    Paginates by positions. Optional filter by CSV `symbols`.
    """
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        symbols_list = None
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

        svc = FactorExposureService(db)
        result = await svc.list_position_exposures(portfolio_id, limit=limit, offset=offset, symbols=symbols_list)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow position-factor-exposures response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Position factor-exposures retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return PositionFactorExposuresResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Position factor exposures failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving position factor exposures")


@router.get("/{portfolio_id}/stress-test", response_model=StressTestResponse)
async def get_stress_test_results(
    portfolio_id: UUID,
    scenarios: str | None = Query(None, description="Optional CSV list of scenario IDs to include"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return precomputed stress testing results for the portfolio using correlated impacts.

    Read-only: joins stored results with scenario definitions; computes percentage and
    new portfolio value using baseline snapshot; no recomputation.
    """
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        scenarios_list = None
        if scenarios:
            scenarios_list = [s.strip() for s in scenarios.split(',') if s.strip()]

        svc = StressTestService(db)
        result = await svc.get_portfolio_results(portfolio_id, scenarios=scenarios_list)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow stress-test response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Stress-test retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return StressTestResponse(**result)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Portfolio not found: {portfolio_id} for user {current_user.id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Stress test retrieval failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving stress test results")


@router.get(
    "/{portfolio_id}/risk-metrics", 
    response_model=PortfolioRiskMetricsResponse,
    deprecated=True,
    summary="⚠️ DEFERRED - Portfolio Risk Metrics (DO NOT USE)",
    description="⚠️ WARNING: PARTIALLY IMPLEMENTED BUT NOT TESTED. DEFERRED INDEFINITELY (2025-09-07). DO NOT USE IN PRODUCTION. Frontend and AI agents should NOT use this endpoint. This endpoint may return incomplete or incorrect data."
)
async def get_portfolio_risk_metrics(
    portfolio_id: UUID,
    lookback_days: int = Query(90, ge=30, le=252, description="Lookback period in days (30–252)"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Portfolio risk metrics (DB-first v1).
    
    ⚠️ WARNING: PARTIALLY IMPLEMENTED BUT NOT TESTED. DEFERRED INDEFINITELY (2025-09-07).
    ⚠️ DO NOT USE IN PRODUCTION. Frontend and AI agents should NOT use this endpoint.
    ⚠️ This endpoint may return incomplete or incorrect data.
    
    Original scope:
    - portfolio_beta from FactorExposure ("Market Beta")
    - annualized_volatility from PortfolioSnapshot.daily_return
    - max_drawdown from PortfolioSnapshot.total_value
    
    Status: Implementation incomplete, testing not performed, deferred for future release.
    """
    # ⚠️ IMPORTANT: This endpoint is DEFERRED INDEFINITELY - DO NOT USE
    # Implementation is incomplete and untested. May return incorrect data.
    # Frontend developers and AI agents should avoid using this endpoint.
    
    try:
        start = time.time()
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)

        svc = RiskMetricsService(db)
        result = await svc.get_portfolio_risk_metrics(portfolio_id, lookback_days=lookback_days)

        elapsed = time.time() - start
        if elapsed > 0.3:
            logger.warning(f"Slow risk-metrics response: {elapsed:.2f}s for portfolio {portfolio_id}")
        else:
            logger.info(f"Risk-metrics retrieved in {elapsed:.3f}s for portfolio {portfolio_id}")

        return PortfolioRiskMetricsResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk metrics failed for {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error retrieving risk metrics")


class UpdateEquityRequest(BaseModel):
    """Request model for updating portfolio equity balance"""
    equity_balance: float
    
    class Config:
        schema_extra = {
            "example": {
                "equity_balance": 1000000.00
            }
        }


@router.put("/{portfolio_id}/equity")
async def update_portfolio_equity(
    portfolio_id: UUID,
    request: UpdateEquityRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the equity balance (NAV) for a portfolio.
    
    This endpoint allows users to set their portfolio's equity balance, which is used
    for calculating cash positions, leverage ratios, and other risk metrics.
    
    Args:
        portfolio_id: The portfolio UUID
        request: The new equity balance value
        
    Returns:
        Success message with updated equity balance
    """
    try:
        # Validate ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        
        # Update equity balance
        stmt = (
            update(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .values(equity_balance=request.equity_balance)
        )
        await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Updated equity balance for portfolio {portfolio_id} to ${request.equity_balance:,.2f}")
        
        return {
            "message": "Equity balance updated successfully",
            "portfolio_id": str(portfolio_id),
            "equity_balance": request.equity_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update equity for {portfolio_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error updating equity balance")
