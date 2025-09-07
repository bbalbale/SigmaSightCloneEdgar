"""
Portfolio Analytics API endpoints

Endpoints for portfolio-level analytics including overview metrics,
exposures, P&L calculations, and performance data.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import time

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.schemas.auth import CurrentUser
from app.schemas.analytics import PortfolioOverviewResponse, CorrelationMatrixResponse
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from app.services.correlation_service import CorrelationService
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
        result = await svc.get_matrix(portfolio_id, lookback_days, min_overlap)
        
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