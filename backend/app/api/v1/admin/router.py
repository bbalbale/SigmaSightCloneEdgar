"""
Admin API router - combines all admin endpoint routers.

Phase 1: Admin authentication (complete)
Phase 1.5: AI data access (complete)
Phase 2: AI tuning system (complete)
"""
from fastapi import APIRouter

from app.api.v1.admin.auth import router as auth_router
from app.api.v1.admin.ai_knowledge import router as ai_knowledge_router
from app.api.v1.admin.ai_tuning import router as ai_tuning_router

# Create the main admin router
admin_router = APIRouter()

# Include admin auth endpoints
admin_router.include_router(auth_router)

# Include AI knowledge base management endpoints
admin_router.include_router(ai_knowledge_router)

# Include AI tuning endpoints (Phase 2)
admin_router.include_router(ai_tuning_router)

# Future admin routers will be added here:
# admin_router.include_router(users_router)
# admin_router.include_router(onboarding_router)
# admin_router.include_router(metrics_router)
