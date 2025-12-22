"""
Admin API router - combines all admin endpoint routers.

Phase 1: Admin authentication (complete)
Phase 1.5: AI data access (complete)
Phase 2: AI tuning system (complete)
Phase 3: User activity tracking (complete)
Phase 4: AI performance metrics (complete)
"""
from fastapi import APIRouter

from app.api.v1.admin.auth import router as auth_router
from app.api.v1.admin.ai_knowledge import router as ai_knowledge_router
from app.api.v1.admin.ai_tuning import router as ai_tuning_router
from app.api.v1.admin.onboarding import router as onboarding_router
from app.api.v1.admin.ai_metrics import router as ai_metrics_router

# Create the main admin router
admin_router = APIRouter()

# Include admin auth endpoints
admin_router.include_router(auth_router)

# Include AI knowledge base management endpoints
admin_router.include_router(ai_knowledge_router)

# Include AI tuning endpoints (Phase 2)
admin_router.include_router(ai_tuning_router)

# Include onboarding analytics endpoints (Phase 3)
admin_router.include_router(onboarding_router)

# Include AI metrics endpoints (Phase 4)
admin_router.include_router(ai_metrics_router)

# Future admin routers will be added here:
# admin_router.include_router(users_router)
