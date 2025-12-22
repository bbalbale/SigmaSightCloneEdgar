"""
Admin API router - combines all admin endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.admin.auth import router as auth_router

# Create the main admin router
admin_router = APIRouter()

# Include admin auth endpoints
admin_router.include_router(auth_router)

# Future admin routers will be added here:
# admin_router.include_router(users_router)
# admin_router.include_router(ai_tuning_router)
# admin_router.include_router(onboarding_router)
# admin_router.include_router(metrics_router)
