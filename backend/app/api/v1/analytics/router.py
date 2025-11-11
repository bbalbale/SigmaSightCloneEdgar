"""
Analytics API Router

Main router for analytics endpoints including portfolio metrics,
risk analytics, and performance data.
"""
from fastapi import APIRouter

from app.api.v1.analytics.portfolio import router as portfolio_router
from app.api.v1.analytics.spread_factors import router as spread_factors_router
from app.api.v1.analytics.aggregate import router as aggregate_router

# Create main analytics router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Include sub-routers
router.include_router(portfolio_router)
router.include_router(spread_factors_router)
router.include_router(aggregate_router)  # Multi-portfolio aggregate analytics