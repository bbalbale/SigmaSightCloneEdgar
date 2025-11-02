"""
Preprocessing Service

Prepares portfolios for batch processing by enriching security master data
and bootstrapping price caches.

This addresses the missing preprocessing steps identified in
ONBOARDING_PIPELINE_COMPARISON.md.

Key responsibilities:
- Extract symbols from portfolio positions
- Enrich security master data (sector/industry)
- Bootstrap historical price cache (30 days)
- Calculate batch readiness (coverage %)
- Handle network failures gracefully

IMPORTANT: This service is transaction-agnostic - it does NOT commit.
The caller (request handler or CLI script) manages the transaction.
"""
from uuid import UUID
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.positions import Position
from app.services.security_master_service import security_master_service
from app.services.price_cache_service import price_cache_service

logger = get_logger(__name__)

# Readiness threshold (80% coverage required)
READINESS_THRESHOLD = 0.80


class PreprocessingService:
    """Service for preparing portfolios for batch processing"""

    @staticmethod
    async def _get_portfolio_symbols(
        portfolio_id: UUID,
        db: AsyncSession
    ) -> List[str]:
        """
        Extract unique symbols from portfolio positions.

        Includes:
        - Main position symbols
        - Underlying symbols for options

        Args:
            portfolio_id: Portfolio UUID
            db: Database session

        Returns:
            List of unique symbols
        """
        result = await db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        positions = result.scalars().all()

        symbols = set()

        for position in positions:
            # Add main symbol (for non-options)
            if position.investment_class != "OPTIONS":
                symbols.add(position.symbol)

            # Add underlying symbol for options
            if position.underlying_symbol:
                symbols.add(position.underlying_symbol)

        unique_symbols = list(symbols)
        logger.info(f"Extracted {len(unique_symbols)} unique symbols from portfolio")

        return unique_symbols

    @staticmethod
    async def prepare_portfolio_for_batch(
        portfolio_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Prepare portfolio for batch processing.

        Steps:
        1. Extract symbols from positions
        2. Enrich security master data
        3. Bootstrap price cache (30 days)
        4. Calculate coverage percentage
        5. Return readiness status

        IMPORTANT: Does NOT commit - caller manages transaction.

        Args:
            portfolio_id: Portfolio UUID
            db: Database session

        Returns:
            Dictionary with preparation metrics:
            {
                "symbols_count": int,
                "security_master_enriched": int,
                "prices_bootstrapped": int,
                "price_coverage_percentage": float,
                "ready_for_batch": bool,
                "network_failure": bool,
                "warnings": List[str],
                "recommendations": List[str]
            }
        """
        result = {
            "symbols_count": 0,
            "security_master_enriched": 0,
            "prices_bootstrapped": 0,
            "price_coverage_percentage": 0.0,
            "ready_for_batch": False,
            "network_failure": False,
            "warnings": [],
            "recommendations": []
        }

        try:
            # Step 1: Extract symbols
            symbols = await PreprocessingService._get_portfolio_symbols(portfolio_id, db)
            result["symbols_count"] = len(symbols)

            if not symbols:
                result["warnings"].append("No symbols found in portfolio")
                return result

            # Step 2: Enrich security master data
            logger.info("Enriching security master data...")
            security_metrics = await security_master_service.enrich_symbols(db, symbols)
            result["security_master_enriched"] = security_metrics["enriched_count"]

            # Step 3: Bootstrap price cache (30 days for onboarding)
            logger.info("Bootstrapping price cache...")
            price_metrics = await price_cache_service.bootstrap_prices(
                db,
                symbols,
                days=30  # Quick bootstrap for onboarding
            )
            result["prices_bootstrapped"] = price_metrics["successful_symbols"]

            # Check for network failure
            if price_metrics["network_failure"]:
                result["network_failure"] = True
                result["warnings"].append(
                    "Price data unavailable due to network issues. "
                    "Batch processing will use entry prices."
                )
                result["recommendations"].append(
                    "Run price update later when network is available"
                )

            # Step 4: Calculate coverage
            coverage_metrics = await price_cache_service.get_price_coverage(db, symbols)
            result["price_coverage_percentage"] = coverage_metrics["coverage_percentage"]

            # Step 5: Determine readiness
            has_sufficient_coverage = (
                result["price_coverage_percentage"] >= (READINESS_THRESHOLD * 100)
            )
            result["ready_for_batch"] = has_sufficient_coverage

            if not has_sufficient_coverage:
                missing_symbols = coverage_metrics.get("missing_symbols", [])
                result["warnings"].append(
                    f"Price coverage below threshold: "
                    f"{result['price_coverage_percentage']:.1f}% "
                    f"(need {READINESS_THRESHOLD * 100}%)"
                )
                result["recommendations"].append(
                    f"Missing prices for: {', '.join(missing_symbols[:5])}"
                    f"{'...' if len(missing_symbols) > 5 else ''}"
                )

            # Log summary
            logger.info(
                f"Preprocessing complete: "
                f"{result['symbols_count']} symbols, "
                f"{result['price_coverage_percentage']:.1f}% coverage, "
                f"ready={result['ready_for_batch']}"
            )

        except Exception as e:
            logger.error(f"Preprocessing failed: {str(e)}", exc_info=True)
            result["warnings"].append(f"Preprocessing error: {str(e)}")
            raise

        return result

    @staticmethod
    async def check_batch_readiness(
        portfolio_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Check if portfolio is ready for batch processing.

        This is a lightweight check that doesn't perform enrichment.
        Use prepare_portfolio_for_batch() to actually prepare the portfolio.

        Args:
            portfolio_id: Portfolio UUID
            db: Database session

        Returns:
            Dictionary with readiness status:
            {
                "ready": bool,
                "security_master_coverage": float,
                "price_coverage": float,
                "missing_symbols": List[str]
            }
        """
        from app.models.market_data import MarketDataCache

        symbols = await PreprocessingService._get_portfolio_symbols(portfolio_id, db)

        if not symbols:
            return {
                "ready": False,
                "security_master_coverage": 0.0,
                "price_coverage": 0.0,
                "missing_symbols": []
            }

        # Check security master coverage
        security_count = 0
        price_count = 0
        missing_symbols = []

        for symbol in symbols:
            result = await db.execute(
                select(MarketDataCache).where(
                    MarketDataCache.symbol == symbol
                ).limit(1)
            )
            cache_entry = result.scalar_one_or_none()

            if cache_entry:
                if cache_entry.sector:
                    security_count += 1
                if cache_entry.close and cache_entry.close > 0:
                    price_count += 1
            else:
                missing_symbols.append(symbol)

        security_coverage = (security_count / len(symbols)) * 100
        price_coverage = (price_count / len(symbols)) * 100

        ready = price_coverage >= (READINESS_THRESHOLD * 100)

        return {
            "ready": ready,
            "security_master_coverage": security_coverage,
            "price_coverage": price_coverage,
            "missing_symbols": missing_symbols
        }


# Convenience instance
preprocessing_service = PreprocessingService()
