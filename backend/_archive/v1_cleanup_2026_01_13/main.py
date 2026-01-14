"""
SigmaSight Backend - FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.router import api_router
from app.core.logging import setup_logging, api_logger
from app.core.onboarding_errors import OnboardingException, create_error_response
from app.core.startup_validation import validate_system_prerequisites, get_prerequisite_status
from app.database import get_async_session, get_ai_session

# Initialize logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="SigmaSight Backend API",
    description="Portfolio risk management backend for SigmaSight",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(OnboardingException)
async def onboarding_exception_handler(request: Request, exc: OnboardingException):
    """Handle onboarding-specific exceptions"""
    api_logger.warning(
        f"Onboarding error: {exc.code} - {exc.message}",
        extra={"code": exc.code, "details": exc.details}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details
        )
    )

# Include API router
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    """Health check endpoint"""
    api_logger.info("Root endpoint accessed")
    return {"message": "SigmaSight Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/health/live")
async def health_liveness():
    """
    V2 Kubernetes liveness probe.

    Always returns 200 if the app is running.
    Used to detect if the app has crashed and needs restart.
    """
    return {"status": "alive"}


@app.get("/health/ready")
async def health_readiness():
    """
    V2 Kubernetes readiness probe.

    Returns:
    - 200: Cache ready OR cold start timeout exceeded (traffic can be served)
    - 503: Cache initializing and timeout not exceeded (hold traffic)
    """
    from fastapi.responses import JSONResponse

    if settings.BATCH_V2_ENABLED:
        from app.cache.symbol_cache import symbol_cache

        if symbol_cache.is_ready():
            return {"status": "ready", "mode": "v2"}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "initializing",
                    "mode": "v2",
                    "message": "Cache warming up, traffic will be served with DB fallback",
                }
            )

    # V1 mode - always ready
    return {"status": "ready", "mode": "v1"}


@app.get("/health/status")
async def health_status():
    """
    V2 Detailed health status for debugging.

    Returns comprehensive health information including cache status.
    """
    result = {
        "batch_v2_enabled": settings.BATCH_V2_ENABLED,
        "status": "healthy",
    }

    if settings.BATCH_V2_ENABLED:
        from app.cache.symbol_cache import symbol_cache

        result["symbol_cache"] = symbol_cache.get_health_status()
        result["ready"] = symbol_cache.is_ready()

    return result

@app.get("/health/prerequisites")
async def health_prerequisites():
    """
    Health check for system prerequisites.

    Returns current status of factor definitions and stress scenarios.
    Useful for deployment health checks and troubleshooting.
    """
    status = await get_prerequisite_status()
    return status

@app.on_event("startup")
async def startup_validation():
    """
    Validate system prerequisites on startup.

    - Development: Logs warnings, doesn't block
    - Production: Blocks startup if prerequisites missing
    - Bypass: Set SKIP_STARTUP_VALIDATION=true
    """
    try:
        api_logger.info("Running startup validation...")
        result = await validate_system_prerequisites()

        if not result["valid"]:
            api_logger.warning("Startup validation completed with warnings")
            for warning in result["warnings"]:
                api_logger.warning(f"  - {warning}")
        else:
            api_logger.info("[OK] Startup validation passed")

    except Exception as e:
        # In production, this will prevent startup
        api_logger.error(f"Startup validation failed: {e}")
        raise


@app.on_event("startup")
async def initialize_v2_cache():
    """
    V2 Symbol Cache initialization (background, non-blocking).

    Only runs when BATCH_V2_ENABLED=true.
    Cache initializes in background - app serves traffic immediately with DB fallback.
    """
    if not settings.BATCH_V2_ENABLED:
        api_logger.info("[V2_CACHE] Skipping cache init (V1 mode)")
        return

    try:
        import asyncio
        from app.cache.symbol_cache import symbol_cache

        api_logger.info("[V2_CACHE] Starting background cache initialization...")

        # Run initialization in background (non-blocking)
        asyncio.create_task(symbol_cache.initialize_async())

        api_logger.info("[V2_CACHE] Background initialization started (app serving with DB fallback)")

    except Exception as e:
        # Don't block startup on cache init failure
        api_logger.warning(f"[V2_CACHE] Failed to start cache init (non-blocking): {e}")


@app.on_event("startup")
async def seed_kb_documents_if_needed():
    """
    Seed AI Knowledge Base documents on startup if below expected count.

    Expected: 36 unique documents (tool docs, domain primers, FAQs)
    Threshold: 30 (allow for minor variations)
    """
    try:
        from app.agent.services.rag_service import count_kb_documents, upsert_kb_document

        # Use AI session for AI tables (ai_kb_documents lives in AI database)
        async with get_ai_session() as db:
            current_count = await count_kb_documents(db)
            api_logger.info(f"[KB] Current document count: {current_count}")

            # Only seed if below expected (36 docs expected)
            # Use upsert, so re-seeding is safe and will update existing + add missing
            if current_count < 36:
                api_logger.info(f"[KB] Document count below threshold (36), seeding KB documents...")

                # Import KB documents from seed script
                from scripts.sigmasightai.seed_kb_documents import KB_DOCUMENTS

                success_count = 0
                for doc in KB_DOCUMENTS:
                    try:
                        await upsert_kb_document(
                            db,
                            scope=doc["scope"],
                            title=doc["title"],
                            content=doc["content"],
                            metadata=doc.get("metadata", {}),
                        )
                        success_count += 1
                    except Exception as e:
                        api_logger.warning(f"[KB] Failed to seed '{doc['title'][:50]}': {e}")

                final_count = await count_kb_documents(db)
                api_logger.info(f"[KB] Seeding complete: {success_count} docs processed, total now: {final_count}")
            else:
                api_logger.info(f"[KB] Document count sufficient ({current_count} >= 36), skipping seed")

    except Exception as e:
        # Don't block startup on KB seeding failure
        api_logger.warning(f"[KB] Failed to seed KB documents (non-blocking): {e}")

@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, 'methods') else None
            })
    return {"routes": routes, "total": len(routes)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
