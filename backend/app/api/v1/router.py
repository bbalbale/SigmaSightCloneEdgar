"""
Main API v1 router that combines all endpoint routers
Updated for v1.4.4 namespace organization
"""
from fastapi import APIRouter

from app.api.v1 import auth, data
from app.api.v1.chat import router as chat_router
from app.api.v1.analytics.router import router as analytics_router
from app.api.v1.target_prices import router as target_prices_router
from app.api.v1.tags import router as tags_router
from app.api.v1.position_tags import router as position_tags_router
from app.api.v1.endpoints import admin_batch

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
api_router.include_router(analytics_router)

# Target Prices APIs (/target-prices/) - portfolio-specific price targets
api_router.include_router(target_prices_router)

# Tag Management APIs (/tags/) - user-scoped organizational tags
api_router.include_router(tags_router)

# Position Tagging APIs (/positions/{id}/tags/) - direct position tagging (new system)
api_router.include_router(position_tags_router, prefix="/positions")

# Admin Batch Processing APIs (/admin/batch/) - batch job control and monitoring
api_router.include_router(admin_batch.router)

# Legacy placeholder and market-data routers are intentionally not registered in v1.2
# (See TODO3.md 6.8/6.9 for removal plan and rationale.)
