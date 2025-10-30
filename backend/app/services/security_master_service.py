"""
Security Master Service

Provides security enrichment functionality extracted from seed_security_master.py.
This service is transaction-agnostic - it does NOT commit/rollback transactions.

Key responsibilities:
- Enrich symbols with sector/industry data
- Query security master data
- Support both static data and API enrichment

Can be used from:
- CLI seeding scripts (which manage their own transactions)
- Request handlers (which manage request-scoped transactions)
"""
from typing import List, Dict, Any
from datetime import date as date_type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.market_data import MarketDataCache

logger = get_logger(__name__)

# Security master data for common symbols
# This is a subset of the full data from seed_security_master.py
SECURITY_MASTER_DATA = {
    # Large Cap Technology Stocks
    "AAPL": {"sector": "Technology", "industry": "Consumer Electronics"},
    "MSFT": {"sector": "Technology", "industry": "Software - Infrastructure"},
    "GOOGL": {"sector": "Communication Services", "industry": "Internet Content & Information"},
    "AMZN": {"sector": "Consumer Discretionary", "industry": "Internet Retail"},
    "NVDA": {"sector": "Technology", "industry": "Semiconductors"},
    "META": {"sector": "Communication Services", "industry": "Internet Content & Information"},
    "TSLA": {"sector": "Consumer Discretionary", "industry": "Auto Manufacturers"},
    "AMD": {"sector": "Technology", "industry": "Semiconductors"},

    # Financial Services
    "JPM": {"sector": "Financial Services", "industry": "Banks - Diversified"},
    "BRK-B": {"sector": "Financial Services", "industry": "Insurance - Diversified"},
    "V": {"sector": "Financial Services", "industry": "Credit Services"},
    "C": {"sector": "Financial Services", "industry": "Banks - Diversified"},

    # Healthcare
    "JNJ": {"sector": "Healthcare", "industry": "Drug Manufacturers - General"},
    "UNH": {"sector": "Healthcare", "industry": "Healthcare Plans"},

    # Consumer/Industrial
    "HD": {"sector": "Consumer Discretionary", "industry": "Home Improvement Retail"},
    "PG": {"sector": "Consumer Staples", "industry": "Household & Personal Products"},
    "GE": {"sector": "Industrials", "industry": "Specialty Industrial Machinery"},

    # Energy
    "XOM": {"sector": "Energy", "industry": "Oil & Gas Integrated"},

    # ETFs
    "SPY": {"sector": "ETF", "industry": "Large Blend"},
    "QQQ": {"sector": "ETF", "industry": "Large Growth"},
    "VTI": {"sector": "ETF", "industry": "Large Blend"},
    "BND": {"sector": "ETF", "industry": "Intermediate Core Bond"},
    "VNQ": {"sector": "ETF", "industry": "Real Estate"},
    "GLD": {"sector": "ETF", "industry": "Commodities Precious Metals"},

    # Default for unknown symbols
    "DEFAULT": {"sector": "Unknown", "industry": "Unknown"}
}


class SecurityMasterService:
    """Service for enriching security master data"""

    @staticmethod
    async def enrich_symbols(
        db: AsyncSession,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Enrich security master data for a list of symbols.

        IMPORTANT: Does NOT commit - caller manages transaction.

        Args:
            db: Database session
            symbols: List of symbols to enrich

        Returns:
            Dictionary with enrichment metrics:
            {
                "enriched_count": int,
                "skipped_count": int,
                "failed_count": int,
                "symbols_enriched": List[str],
                "symbols_skipped": List[str],
                "symbols_failed": List[str]
            }
        """
        metrics = {
            "enriched_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "symbols_enriched": [],
            "symbols_skipped": [],
            "symbols_failed": []
        }

        for symbol in symbols:
            try:
                # Check if we already have security master data
                result = await db.execute(
                    select(MarketDataCache).where(
                        MarketDataCache.symbol == symbol
                    ).limit(1)
                )
                existing = result.scalar_one_or_none()

                if existing and existing.sector:
                    # Already have sector data
                    metrics["skipped_count"] += 1
                    metrics["symbols_skipped"].append(symbol)
                    logger.debug(f"Security master data already exists for {symbol}")
                    continue

                # Get security master data (static or API)
                data = SECURITY_MASTER_DATA.get(symbol, SECURITY_MASTER_DATA["DEFAULT"])

                if not existing:
                    # Create new entry
                    cache_entry = MarketDataCache(
                        symbol=symbol,
                        date=date_type.today(),
                        close=0.0,  # Placeholder - will be updated by price bootstrap
                        sector=data["sector"],
                        industry=data["industry"],
                        data_source="security_master_service"
                    )
                    db.add(cache_entry)
                    logger.debug(f"Created security master record for {symbol}")
                else:
                    # Update existing entry
                    existing.sector = data["sector"]
                    existing.industry = data["industry"]
                    logger.debug(f"Updated security master data for {symbol}")

                metrics["enriched_count"] += 1
                metrics["symbols_enriched"].append(symbol)

            except Exception as e:
                logger.error(f"Failed to enrich {symbol}: {str(e)}")
                metrics["failed_count"] += 1
                metrics["symbols_failed"].append(symbol)

        logger.info(
            f"Security master enrichment: "
            f"{metrics['enriched_count']} enriched, "
            f"{metrics['skipped_count']} skipped, "
            f"{metrics['failed_count']} failed"
        )

        return metrics


# Convenience instance
security_master_service = SecurityMasterService()
