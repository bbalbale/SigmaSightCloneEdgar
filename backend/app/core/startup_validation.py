"""
Startup Validation

Validates system prerequisites are properly seeded before accepting requests.

Checks:
- Factor definitions (8 required)
- Stress test scenarios (18 required)

Modes:
- Development: Warnings only (non-blocking)
- Production: Strict enforcement (blocks startup if prerequisites missing)
- Bypass: SKIP_STARTUP_VALIDATION=true environment variable

This ensures batch processing has necessary reference data to function correctly.
"""
import os
from typing import Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.database import AsyncSessionLocal

logger = get_logger(__name__)

# Required prerequisites
MIN_FACTOR_DEFINITIONS = 8
MIN_STRESS_SCENARIOS = 18


async def check_factor_definitions(db: AsyncSession) -> int:
    """
    Check if factor definitions are seeded.

    Returns:
        Number of factor definitions found
    """
    try:
        from app.models.market_data import FactorDefinition

        result = await db.execute(
            select(func.count(FactorDefinition.id))
        )
        count = result.scalar()
        return count or 0

    except Exception as e:
        logger.error(f"Failed to check factor definitions: {e}")
        return 0


async def check_stress_scenarios(db: AsyncSession) -> int:
    """
    Check if stress test scenarios are seeded.

    Returns:
        Number of stress scenarios found
    """
    try:
        from app.models.market_data import StressTestScenario

        result = await db.execute(
            select(func.count(StressTestScenario.id))
        )
        count = result.scalar()
        return count or 0

    except Exception as e:
        logger.error(f"Failed to check stress scenarios: {e}")
        return 0


async def validate_system_prerequisites() -> Dict[str, Any]:
    """
    Validate system prerequisites are seeded.

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "factor_count": int,
            "scenario_count": int,
            "warnings": List[str],
            "recommendations": List[str]
        }

    Behavior:
    - SKIP_STARTUP_VALIDATION=true: Skip validation entirely
    - Development mode: Log warnings, don't block startup
    - Production mode: Raise RuntimeError if prerequisites missing
    """
    result = {
        "valid": True,
        "factor_count": 0,
        "scenario_count": 0,
        "warnings": [],
        "recommendations": []
    }

    # Check for bypass flag
    if os.getenv("SKIP_STARTUP_VALIDATION", "").lower() == "true":
        logger.warning("WARNING: Startup validation SKIPPED (SKIP_STARTUP_VALIDATION=true)")
        result["warnings"].append("Startup validation bypassed via environment variable")
        return result

    # Determine strict mode
    is_production = settings.ENVIRONMENT.lower() in ["production", "prod"]
    strict_mode = is_production

    if strict_mode:
        logger.info("🔒 Production mode - validation enforced")
    else:
        logger.info("[TOOL] Development mode - validation warnings only")

    # Check prerequisites
    async with AsyncSessionLocal() as db:
        try:
            result["factor_count"] = await check_factor_definitions(db)
            result["scenario_count"] = await check_stress_scenarios(db)

            # Validate counts
            missing_factors = max(0, MIN_FACTOR_DEFINITIONS - result["factor_count"])
            missing_scenarios = max(0, MIN_STRESS_SCENARIOS - result["scenario_count"])

            if missing_factors > 0 or missing_scenarios > 0:
                result["valid"] = False

                # Build error message
                error_parts = []
                if missing_factors > 0:
                    error_parts.append(
                        f"{result['factor_count']}/{MIN_FACTOR_DEFINITIONS} factors "
                        f"(missing {missing_factors})"
                    )
                if missing_scenarios > 0:
                    error_parts.append(
                        f"{result['scenario_count']}/{MIN_STRESS_SCENARIOS} scenarios "
                        f"(missing {missing_scenarios})"
                    )

                error_msg = (
                    f"System prerequisites incomplete: {', '.join(error_parts)}. "
                    f"Run: cd backend && uv run python scripts/database/seed_database.py"
                )

                result["warnings"].append(error_msg)
                result["recommendations"].append(
                    "Seed demo data: cd backend && uv run python scripts/database/seed_database.py"
                )

                if strict_mode:
                    # Production: Block startup
                    logger.error(f"[ERROR] {error_msg}")
                    raise RuntimeError(error_msg)
                else:
                    # Development: Warn only
                    logger.warning(f"WARNING: {error_msg}")

            else:
                # All prerequisites present
                logger.info(
                    f"[OK] System prerequisites validated: "
                    f"{result['factor_count']} factors, "
                    f"{result['scenario_count']} scenarios"
                )

        except RuntimeError:
            # Re-raise production errors
            raise
        except Exception as e:
            logger.error(f"Startup validation failed: {e}", exc_info=True)
            result["valid"] = False
            result["warnings"].append(f"Validation error: {str(e)}")

            if strict_mode:
                raise RuntimeError(f"Startup validation failed: {e}")

    return result


async def get_prerequisite_status() -> Dict[str, Any]:
    """
    Get current prerequisite status for health check endpoint.

    Returns:
        Dictionary with current counts and status
    """
    async with AsyncSessionLocal() as db:
        try:
            factor_count = await check_factor_definitions(db)
            scenario_count = await check_stress_scenarios(db)

            return {
                "factors": {
                    "current": factor_count,
                    "required": MIN_FACTOR_DEFINITIONS,
                    "status": "ok" if factor_count >= MIN_FACTOR_DEFINITIONS else "incomplete"
                },
                "scenarios": {
                    "current": scenario_count,
                    "required": MIN_STRESS_SCENARIOS,
                    "status": "ok" if scenario_count >= MIN_STRESS_SCENARIOS else "incomplete"
                },
                "overall_status": (
                    "ok" if (factor_count >= MIN_FACTOR_DEFINITIONS and
                            scenario_count >= MIN_STRESS_SCENARIOS)
                    else "incomplete"
                )
            }

        except Exception as e:
            logger.error(f"Failed to get prerequisite status: {e}")
            return {
                "factors": {"current": 0, "required": MIN_FACTOR_DEFINITIONS, "status": "error"},
                "scenarios": {"current": 0, "required": MIN_STRESS_SCENARIOS, "status": "error"},
                "overall_status": "error",
                "error": str(e)
            }
