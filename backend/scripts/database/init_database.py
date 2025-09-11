#!/usr/bin/env python3
"""
Database initialization script for SigmaSight Backend
Creates all database tables using SQLAlchemy models
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import engine, Base
from app.core.logging import setup_logging, get_logger

# Import all models to register them with Base
from app.models.users import User, Portfolio
from app.models.positions import Position, Tag
from app.models.market_data import (
    MarketDataCache, PositionGreeks, FactorDefinition, FactorExposure,
    PositionFactorExposure, MarketRiskScenario, PositionInterestRateBeta,
    StressTestScenario, StressTestResult, FactorCorrelation, FundHoldings
)
from app.models.snapshots import PortfolioSnapshot, BatchJob, BatchJobSchedule
from app.models.correlations import (
    CorrelationCalculation, CorrelationCluster, 
    CorrelationClusterPosition, PairwiseCorrelation
)
from app.models.history import ExportHistory
from app.models.modeling import ModelingSessionSnapshot

# Setup logging
setup_logging()
logger = get_logger("init_database")

async def main():
    """Initialize database tables"""
    try:
        logger.info("Starting database initialization...")
        
        # Create all tables using the imported models
        async with engine.begin() as conn:
            logger.info("Creating all database tables...")
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("✅ Database initialization completed successfully!")
        print("✅ All database tables created successfully")
        
        print("✅ Database tables created (verification via Docker)")
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())