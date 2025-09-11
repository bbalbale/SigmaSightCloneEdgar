"""
Database seeding script for SigmaSight Backend - Section 1.5 Implementation
Orchestrates all seeding operations for demo data
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import get_async_session
from app.core.logging import setup_logging, get_logger
from app.db.seed_factors import seed_factors
from app.db.seed_demo_portfolios import seed_demo_portfolios
from app.db.seed_security_master import seed_security_master
from app.db.seed_initial_prices import seed_initial_prices

# Setup logging
setup_logging()
logger = get_logger("seed_database")

async def seed_database():
    """
    Section 1.5 Demo Data Seeding - Complete Implementation
    
    Orchestrates seeding in proper dependency order:
    1. Core Infrastructure (users, factors)
    2. Demo Portfolio Structure (portfolios, positions, tags)
    3. Essential Data for Batch Processing (security master, initial prices)
    """
    start_time = datetime.now()
    logger.info("🚀 Starting Section 1.5 Demo Data Seeding...")
    
    async with get_async_session() as db:
        try:
            # Step 1: Core Infrastructure (already implemented)
            logger.info("📋 Step 1: Seeding core infrastructure...")
            
            # Seed factor definitions (8 factors for risk analysis)
            await seed_factors(db)
            logger.info("✅ Factor definitions seeded")
            
            # Create demo users first
            logger.info("Creating demo users...")
            from app.db.seed_demo_portfolios import create_demo_users
            
            await create_demo_users(db)
            
            await db.commit()
            logger.info("✅ Demo users created")
            
            # Step 2: Demo Portfolio Structure
            logger.info("🏗️ Step 2: Creating demo portfolio structures...")
            await seed_demo_portfolios(db)
            logger.info("✅ Demo portfolios created with positions and tags")
            
            # Step 3: Essential Data for Batch Processing
            logger.info("🔧 Step 3: Preparing batch processing prerequisites...")
            
            # Seed stress test scenarios (required for stress testing API)
            logger.info("🌱 Seeding stress test scenarios...")
            from scripts.seed_stress_scenarios import seed_scenarios_from_config
            await seed_scenarios_from_config()
            logger.info("✅ Stress test scenarios seeded")
            
            # Seed security master data (classifications for factor analysis)
            await seed_security_master(db)
            logger.info("✅ Security master data populated")
            
            # Bootstrap initial prices (required for batch job 1)
            await seed_initial_prices(db)
            logger.info("✅ Initial price cache bootstrapped")
            
            await db.commit()
            
            duration = datetime.now() - start_time
            logger.info(f"🎯 Section 1.5 Demo Data Seeding completed successfully in {duration}")
            logger.info("📊 Demo portfolios are now ready for batch processing framework!")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Database seeding failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(seed_database())
