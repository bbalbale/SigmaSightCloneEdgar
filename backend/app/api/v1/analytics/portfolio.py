"""
Portfolio Analytics API endpoints

Endpoints for portfolio-level analytics including overview metrics,
exposures, P&L calculations, and performance data.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.schemas.auth import CurrentUser
from app.schemas.analytics import PortfolioOverviewResponse
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
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