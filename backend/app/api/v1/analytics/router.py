"""
Analytics API Router

Main router for analytics endpoints including portfolio metrics,
risk analytics, and performance data.
"""
from fastapi import APIRouter

from app.api.v1.analytics.portfolio import router as portfolio_router

# Create main analytics router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Include sub-routers
router.include_router(portfolio_router)