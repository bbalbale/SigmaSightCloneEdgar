"""
V2 Health Check Endpoints

Provides Kubernetes/Railway-compatible health probes:
- /health/live: Liveness probe (always 200 if app is running)
- /health/ready: Readiness probe (503 until cache ready OR timeout)
- /health/status: Detailed health status (for debugging)

Reference: PlanningDocs/V2BatchArchitecture/19-IMPLEMENTATION-FIXES.md Section 1
"""

from fastapi import APIRouter, Response, status
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe.

    Always returns 200 if the app is running.
    Used to detect if the app has crashed and needs restart.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(response: Response):
    """
    Kubernetes readiness probe.

    Returns:
    - 200: Cache ready OR cold start timeout exceeded (traffic can be served)
    - 503: Cache initializing and timeout not exceeded (hold traffic)

    In V2 mode, checks symbol cache readiness.
    In V1 mode, always returns ready.
    """
    if settings.BATCH_V2_ENABLED:
        from app.cache.symbol_cache import symbol_cache

        if symbol_cache.is_ready():
            return {"status": "ready", "mode": "v2"}
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "initializing",
                "mode": "v2",
                "message": "Cache warming up, traffic will be served with DB fallback",
            }

    # V1 mode - always ready
    return {"status": "ready", "mode": "v1"}


@router.get("/health/status")
async def health_status():
    """
    Detailed health status for debugging.

    Returns comprehensive health information including:
    - Cache initialization status
    - Stats and counts
    - V2 mode detection
    """
    result = {
        "batch_v2_enabled": settings.BATCH_V2_ENABLED,
        "status": "healthy",
    }

    if settings.BATCH_V2_ENABLED:
        from app.cache.symbol_cache import symbol_cache

        result["symbol_cache"] = symbol_cache.get_health_status()
        result["ready"] = symbol_cache.is_ready()
        result["alive"] = symbol_cache.is_alive()

    return result
