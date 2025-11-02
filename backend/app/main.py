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
            api_logger.info("✅ Startup validation passed")

    except Exception as e:
        # In production, this will prevent startup
        api_logger.error(f"Startup validation failed: {e}")
        raise

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
