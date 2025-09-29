"""
Security Master Data Seeding - Section 1.5 Implementation
Enriches demo portfolio symbols with sector, industry, and classification data required for batch processing
"""
import asyncio
from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.logging import get_logger
from app.models.market_data import MarketDataCache
from app.services.market_data_service import market_data_service

logger = get_logger(__name__)

# Security master data for all demo portfolio symbols
# This data enables factor exposure calculations in Batch Job 3
SECURITY_MASTER_DATA = {
    # Large Cap Technology Stocks
    "AAPL": {"sector": "Technology", "industry": "Consumer Electronics", "market_cap": 3500000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "MSFT": {"sector": "Technology", "industry": "Software - Infrastructure", "market_cap": 3200000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "GOOGL": {"sector": "Communication Services", "industry": "Internet Content & Information", "market_cap": 2100000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "AMZN": {"sector": "Consumer Discretionary", "industry": "Internet Retail", "market_cap": 1800000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "NVDA": {"sector": "Technology", "industry": "Semiconductors", "market_cap": 1700000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "META": {"sector": "Communication Services", "industry": "Internet Content & Information", "market_cap": 1300000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "TSLA": {"sector": "Consumer Discretionary", "industry": "Auto Manufacturers", "market_cap": 800000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "AMD": {"sector": "Technology", "industry": "Semiconductors", "market_cap": 230000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    
    # Financial Services
    "JPM": {"sector": "Financial Services", "industry": "Banks - Diversified", "market_cap": 650000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    "BRK-B": {"sector": "Financial Services", "industry": "Insurance - Diversified", "market_cap": 900000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    "V": {"sector": "Financial Services", "industry": "Credit Services", "market_cap": 550000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    "C": {"sector": "Financial Services", "industry": "Banks - Diversified", "market_cap": 110000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    
    # Healthcare
    "JNJ": {"sector": "Healthcare", "industry": "Drug Manufacturers - General", "market_cap": 450000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    "UNH": {"sector": "Healthcare", "industry": "Healthcare Plans", "market_cap": 500000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    
    # Consumer/Industrial
    "HD": {"sector": "Consumer Discretionary", "industry": "Home Improvement Retail", "market_cap": 420000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    "PG": {"sector": "Consumer Staples", "industry": "Household & Personal Products", "market_cap": 380000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    "GE": {"sector": "Industrials", "industry": "Specialty Industrial Machinery", "market_cap": 180000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    
    # Energy
    "XOM": {"sector": "Energy", "industry": "Oil & Gas Integrated", "market_cap": 450000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    
    # Automotive
    "F": {"sector": "Consumer Discretionary", "industry": "Auto Manufacturers", "market_cap": 50000000000, "security_type": "stock", "exchange": "NYSE", "country": "US"},
    
    # Media/Entertainment
    "NFLX": {"sector": "Communication Services", "industry": "Entertainment", "market_cap": 200000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    
    # E-commerce/Technology (Shorts)
    "SHOP": {"sector": "Technology", "industry": "Software - Application", "market_cap": 25000000000, "security_type": "stock", "exchange": "NYSE", "country": "CA"},
    "ZOOM": {"sector": "Technology", "industry": "Software - Application", "market_cap": 20000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "PTON": {"sector": "Consumer Discretionary", "industry": "Leisure", "market_cap": 1500000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    "ROKU": {"sector": "Communication Services", "industry": "Entertainment", "market_cap": 4000000000, "security_type": "stock", "exchange": "NASDAQ", "country": "US"},
    
    # ETFs - Broad Market
    "SPY": {"sector": "ETF", "industry": "Large Blend", "market_cap": 500000000000, "security_type": "etf", "exchange": "NYSE", "country": "US"},
    "QQQ": {"sector": "ETF", "industry": "Large Growth", "market_cap": 220000000000, "security_type": "etf", "exchange": "NASDAQ", "country": "US"},
    "VTI": {"sector": "ETF", "industry": "Large Blend", "market_cap": 350000000000, "security_type": "etf", "exchange": "NYSE", "country": "US"},
    "BND": {"sector": "ETF", "industry": "Intermediate Core Bond", "market_cap": 90000000000, "security_type": "etf", "exchange": "NASDAQ", "country": "US"},
    "VNQ": {"sector": "ETF", "industry": "Real Estate", "market_cap": 35000000000, "security_type": "etf", "exchange": "NYSE", "country": "US"},
    
    # Commodity/Alternative ETFs
    "GLD": {"sector": "ETF", "industry": "Commodities Precious Metals", "market_cap": 60000000000, "security_type": "etf", "exchange": "NYSE", "country": "US"},
    "DJP": {"sector": "ETF", "industry": "Commodities Broad Basket", "market_cap": 2000000000, "security_type": "etf", "exchange": "NYSE", "country": "US"},
    
    # Mutual Funds - Fidelity
    "FXNAX": {"sector": "Mutual Fund", "industry": "Large Growth", "market_cap": 45000000000, "security_type": "mutual_fund", "exchange": "OTC", "country": "US"},
    "FCNTX": {"sector": "Mutual Fund", "industry": "Large Blend", "market_cap": 130000000000, "security_type": "mutual_fund", "exchange": "OTC", "country": "US"},
    "FMAGX": {"sector": "Mutual Fund", "industry": "Large Blend", "market_cap": 25000000000, "security_type": "mutual_fund", "exchange": "OTC", "country": "US"},
    
    # Mutual Funds - Vanguard
    "VTIAX": {"sector": "Mutual Fund", "industry": "Foreign Large Blend", "market_cap": 380000000000, "security_type": "mutual_fund", "exchange": "OTC", "country": "US"},
    
    # Options Underlyings (handled by parent stock classifications)
    "VIX": {"sector": "Index", "industry": "Volatility Index", "market_cap": 0, "security_type": "index", "exchange": "CBOE", "country": "US"},
}

# Extract all unique symbols from demo portfolios
def get_all_demo_symbols() -> List[str]:
    """Extract all unique symbols from demo portfolios including options underlyings"""
    symbols = set()
    
    # Import here to avoid circular imports
    from app.db.seed_demo_portfolios import DEMO_PORTFOLIOS
    
    for portfolio in DEMO_PORTFOLIOS:
        for position in portfolio["positions"]:
            symbol = position["symbol"]
            
            # Add the main symbol
            if len(symbol) > 10 and any(c in symbol for c in ['C', 'P']):
                # Options symbol - add underlying
                if "underlying" in position:
                    symbols.add(position["underlying"])
            else:
                # Stock/ETF/Fund symbol
                symbols.add(symbol)
    
    return list(symbols)

async def seed_security_master_data(db: AsyncSession, symbol: str, data: Dict[str, Any]) -> bool:
    """Seed security master data for a single symbol"""
    try:
        # Check if we already have market data for this symbol (any date)
        result = await db.execute(
            select(MarketDataCache).where(MarketDataCache.symbol == symbol).limit(1)
        )
        existing = result.scalar_one_or_none()
        
        if existing and existing.sector:
            logger.debug(f"Security master data already exists for {symbol}")
            return False
        
        # Create or update market data cache entry with security master data
        if not existing:
            # Create new entry with placeholder price data
            cache_entry = MarketDataCache(
                symbol=symbol,
                date=date.today(),  # Will be updated by price seeding
                close=0.0,  # Placeholder - will be updated by initial price seeding
                sector=data["sector"],
                industry=data["industry"],
                data_source="seed_security_master"
            )
            db.add(cache_entry)
            logger.debug(f"Created security master record for {symbol}")
        else:
            # Update existing entry with sector/industry data
            existing.sector = data["sector"]
            existing.industry = data["industry"]
            logger.debug(f"Updated security master data for {symbol}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed security master data for {symbol}: {e}")
        return False

async def enrich_from_api(db: AsyncSession, symbol: str) -> bool:
    """Try to enrich security data from API if not in our static data"""
    try:
        logger.info(f"🔍 Fetching security data from API for {symbol}")
        
        # Use Section 1.4.9 market data service to get security information
        # This would typically call FMP or Polygon APIs for sector/industry data
        # For now, we'll use a placeholder implementation
        
        # Note: In a full implementation, this would call:
        # security_info = await market_data_service.get_security_info(symbol)
        
        # Placeholder - mark as unknown for now
        cache_entry = MarketDataCache(
            symbol=symbol,
            date=date.today(),
            close=0.0,  # Placeholder
            sector="Unknown",
            industry="Unknown",
            data_source="api_enrichment"
        )
        db.add(cache_entry)
        
        logger.warning(f"⚠️ Added placeholder security data for {symbol} - needs API enrichment")
        return True
        
    except Exception as e:
        logger.error(f"Failed to enrich {symbol} from API: {e}")
        return False

async def seed_security_master(db: AsyncSession) -> None:
    """Seed security master data for all demo portfolio symbols"""
    logger.info("🔧 Seeding security master data...")
    
    # Get all symbols from demo portfolios
    demo_symbols = get_all_demo_symbols()
    logger.info(f"Processing {len(demo_symbols)} unique symbols from demo portfolios")
    
    seeded_count = 0
    enriched_count = 0
    
    for symbol in demo_symbols:
        if symbol in SECURITY_MASTER_DATA:
            # Use our static data
            success = await seed_security_master_data(db, symbol, SECURITY_MASTER_DATA[symbol])
            if success:
                seeded_count += 1
        else:
            # Try to enrich from API
            success = await enrich_from_api(db, symbol)
            if success:
                enriched_count += 1
    
    logger.info(f"✅ Security master data: {seeded_count} seeded, {enriched_count} API enriched")
    
    if enriched_count > 0:
        logger.warning(f"⚠️ {enriched_count} symbols need API enrichment for production readiness")

async def main():
    """Main function for testing"""
    from app.database import get_async_session
    
    async with get_async_session() as db:
        try:
            await seed_security_master(db)
            await db.commit()
            logger.info("✅ Security master seeding completed")
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Security master seeding failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())