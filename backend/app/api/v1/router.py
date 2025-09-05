"""
Main API v1 router that combines all endpoint routers
Updated for v1.4.4 namespace organization
"""
from fastapi import APIRouter

from app.api.v1 import auth, portfolio, positions, risk, modeling, market_data, data
from app.api.v1.chat import router as chat_router
from app.api.v1.analytics import router as analytics_router

# Create the main v1 router
api_router = APIRouter(prefix="/v1")

# Include all endpoint routers
# Authentication (foundation)
api_router.include_router(auth.router)

# Chat API for Agent
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])

# Raw Data APIs (/data/) - for LLM consumption
api_router.include_router(data.router)

# Analytics APIs (/analytics/) - calculated metrics  
api_router.include_router(analytics_router.router)

# Legacy endpoints (to be reorganized)
api_router.include_router(portfolio.router)
api_router.include_router(positions.router)
api_router.include_router(risk.router)
api_router.include_router(modeling.router)
api_router.include_router(market_data.router)
