"""
V2 Onboarding Service

Orchestrates fast portfolio onboarding using V2 batch architecture.
Handles both known and unknown symbols efficiently.

Key Design:
- Uses pre-computed symbol data from nightly V2 batch when available
- Processes unknown symbols on-demand (Phases 0, 1, 3)
- Runs portfolio calculations using V2 caches (Phases 4, 5, 6)
- Returns within seconds for known symbols, 30-60s with unknown symbols

Reference: PlanningDocs/V2BatchArchitecture/22-ONBOARDING-INTEGRATION.md
"""

import time
from datetime import date
from typing import Dict, List, Set, Tuple, Any, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.trading_calendar import get_most_recent_completed_trading_day
from app.database import get_async_session
from app.models.positions import Position
from app.models.symbol_analytics import SymbolFactorExposure

logger = get_logger(__name__)

V2_LOG_PREFIX = "[V2_ONBOARDING]"


class V2OnboardingService:
    """
    Fast-path onboarding using V2 batch architecture.

    Flow:
    1. Classify portfolio symbols (known vs unknown)
    2. Process unknown symbols (Phases 0, 1, 3) - scoped batch
    3. Run portfolio calculations (Phases 4, 5, 6) - using caches
    """

    async def run_onboarding_calculations(
        self,
        portfolio_id: UUID,
        calculation_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Run V2 onboarding calculations for a portfolio.

        This is the main entry point for V2 onboarding. It:
        1. Classifies symbols as known (in cache) or unknown (need processing)
        2. Processes unknown symbols via scoped Phase 0/1/3
        3. Runs portfolio Phases 4/5/6 using cached data

        Args:
            portfolio_id: Portfolio to process
            calculation_date: Date for calculations (defaults to most recent trading day)

        Returns:
            Dict with processing results and timing
        """
        start_time = time.time()

        if calculation_date is None:
            calculation_date = get_most_recent_completed_trading_day()

        logger.info(
            f"{V2_LOG_PREFIX} Starting onboarding for portfolio {portfolio_id} "
            f"(calc_date={calculation_date})"
        )

        result = {
            "success": True,
            "portfolio_id": str(portfolio_id),
            "calculation_date": calculation_date.isoformat(),
            "symbols": {},
            "phases": {},
            "errors": [],
        }

        try:
            # Step 1: Classify symbols
            known, unknown = await self._classify_symbols(portfolio_id, calculation_date)
            result["symbols"] = {
                "total": len(known) + len(unknown),
                "known": len(known),
                "unknown": len(unknown),
                "unknown_list": list(unknown)[:20],  # Limit for response size
            }

            logger.info(
                f"{V2_LOG_PREFIX} Symbol classification: "
                f"{len(known)} known, {len(unknown)} unknown"
            )

            # Step 2: Process unknown symbols (if any)
            if unknown:
                from app.batch.v2.symbol_batch_runner import run_symbol_batch_for_symbols

                logger.info(f"{V2_LOG_PREFIX} Processing {len(unknown)} unknown symbols...")
                symbol_result = await run_symbol_batch_for_symbols(
                    symbols=list(unknown),
                    target_date=calculation_date,
                )
                result["phases"]["symbol_processing"] = symbol_result

                if not symbol_result.get("success", False):
                    result["errors"].extend(symbol_result.get("errors", []))
            else:
                result["phases"]["symbol_processing"] = {
                    "success": True,
                    "skipped": True,
                    "reason": "all_symbols_known",
                }

            # Step 3: Run portfolio calculations (Phases 4-6)
            from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh_for_portfolio

            logger.info(f"{V2_LOG_PREFIX} Running portfolio calculations...")
            portfolio_result = await run_portfolio_refresh_for_portfolio(
                portfolio_id=portfolio_id,
                target_date=calculation_date,
            )
            result["phases"]["portfolio_refresh"] = portfolio_result

            if not portfolio_result.get("success", False):
                result["errors"].extend(portfolio_result.get("errors", []))
                result["success"] = False

        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} Onboarding failed: {e}", exc_info=True)
            result["success"] = False
            result["errors"].append(str(e))

        result["duration_seconds"] = round(time.time() - start_time, 2)

        logger.info(
            f"{V2_LOG_PREFIX} Onboarding complete: success={result['success']}, "
            f"duration={result['duration_seconds']}s"
        )

        return result

    async def _classify_symbols(
        self,
        portfolio_id: UUID,
        calculation_date: date,
    ) -> Tuple[Set[str], Set[str]]:
        """
        Classify portfolio symbols as known or unknown.

        Known = has factors in symbol_factor_exposures for calculation_date
        Unknown = needs on-demand processing

        Args:
            portfolio_id: Portfolio to check
            calculation_date: Date to check factors for

        Returns:
            (known_symbols, unknown_symbols)
        """
        async with get_async_session() as db:
            # Get portfolio symbols from active positions
            result = await db.execute(
                select(Position.symbol)
                .where(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.exit_date.is_(None),  # Active positions only
                        Position.symbol.isnot(None),
                        Position.symbol != '',
                    )
                )
                .distinct()
            )
            portfolio_symbols = {row[0].upper() for row in result.all() if row[0]}

            if not portfolio_symbols:
                return set(), set()

            # Check which symbols have factors for this date
            result = await db.execute(
                select(SymbolFactorExposure.symbol)
                .where(
                    and_(
                        SymbolFactorExposure.symbol.in_(portfolio_symbols),
                        SymbolFactorExposure.calculation_date == calculation_date,
                    )
                )
                .distinct()
            )
            symbols_with_factors = {row[0].upper() for row in result.all() if row[0]}

            known = portfolio_symbols & symbols_with_factors
            unknown = portfolio_symbols - symbols_with_factors

            return known, unknown


# Global instance
v2_onboarding_service = V2OnboardingService()
