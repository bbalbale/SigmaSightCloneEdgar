"""
Database Reset and Seed Utility - Section 1.5 Implementation
Complete database reset and reseed utility for clean demo environment setup
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import get_async_session, engine, Base
from app.core.logging import setup_logging, get_logger

# Import seeding functions
from scripts.seed_database import seed_database

# Setup logging
setup_logging()
logger = get_logger("reset_and_seed")

async def reset_database():
    """
    DANGEROUS: Drop all tables and recreate schema
    Only use in development environments!
    """
    logger.warning("⚠️ DESTRUCTIVE OPERATION: Dropping all database tables...")
    
    # Confirm this is not production
    from app.config import settings
    
    if "prod" in settings.DATABASE_URL.lower() or "production" in settings.DATABASE_URL.lower():
        raise ValueError("❌ SAFETY CHECK: Cannot reset production database!")
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("💥 All tables dropped")
        
        # Recreate all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("🏗️ Database schema recreated")

async def validate_demo_environment():
    """Validate that demo data was seeded correctly"""
    logger.info("🔍 Validating demo environment...")
    
    async with get_async_session() as db:
        from sqlalchemy import select, func
        from app.models.users import User, Portfolio
        from app.models.positions import Position
        from app.models.market_data import MarketDataCache, FactorDefinition
        
        # Check users
        user_count = await db.scalar(select(func.count(User.id)))
        logger.info(f"👥 Demo users: {user_count}")
        
        # Check portfolios
        portfolio_count = await db.scalar(select(func.count(Portfolio.id)))
        logger.info(f"📊 Demo portfolios: {portfolio_count}")
        
        # Check positions
        position_count = await db.scalar(select(func.count(Position.id)))
        logger.info(f"🔢 Total positions: {position_count}")
        
        # Check market data
        market_data_count = await db.scalar(select(func.count(MarketDataCache.id)))
        logger.info(f"💰 Market data records: {market_data_count}")
        
        # Check factors
        factor_count = await db.scalar(select(func.count(FactorDefinition.id)))
        logger.info(f"📈 Factor definitions: {factor_count}")
        
        # Check positions with market values
        positions_with_values = await db.scalar(
            select(func.count(Position.id)).where(Position.market_value.isnot(None))
        )
        logger.info(f"💵 Positions with market values: {positions_with_values}")
        
        # Validation checks
        validation_passed = True
        
        if user_count < 3:
            logger.error("❌ Expected at least 3 demo users")
            validation_passed = False
            
        if portfolio_count < 3:
            logger.error("❌ Expected at least 3 demo portfolios") 
            validation_passed = False
            
        if position_count < 50:
            logger.error("❌ Expected at least 50 demo positions")
            validation_passed = False
            
        if factor_count != 8:
            logger.error("❌ Expected exactly 8 factor definitions")
            validation_passed = False
            
        if market_data_count < 30:
            logger.error("❌ Expected market data for at least 30 symbols")
            validation_passed = False
            
        if positions_with_values < (position_count * 0.8):
            logger.error("❌ Less than 80% of positions have market values")
            validation_passed = False
        
        if validation_passed:
            logger.info("✅ Demo environment validation passed!")
        else:
            logger.error("❌ Demo environment validation failed!")
            
        return validation_passed

async def reset_and_seed():
    """Complete reset and seed workflow"""
    start_time = datetime.now()
    logger.info("🚀 Starting complete database reset and seed...")
    
    try:
        # Step 1: Reset database (DANGEROUS!)
        logger.info("🔄 Step 1: Resetting database...")
        await reset_database()
        
        # Step 2: Run complete seeding
        logger.info("📡 Step 2: Running complete demo data seeding...")
        await seed_database()
        
        # Step 3: Validate environment
        logger.info("✅ Step 3: Validating demo environment...")
        validation_passed = await validate_demo_environment()
        
        duration = datetime.now() - start_time
        
        if validation_passed:
            logger.info(f"🎯 Database reset and seed completed successfully in {duration}")
            logger.info("🚀 Demo environment is ready for development and testing!")
            logger.info("")
            logger.info("Demo User Credentials:")
            logger.info("  Individual Investor: demo_individual@sigmasight.com / demo12345")
            logger.info("  High Net Worth: demo_hnw@sigmasight.com / demo12345")
            logger.info("  Hedge Fund Style: demo_hedgefundstyle@sigmasight.com / demo12345")
        else:
            logger.error("❌ Reset and seed completed but validation failed")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Reset and seed failed: {e}")
        raise

async def seed_only():
    """Seed demo data without resetting (safer option)"""
    start_time = datetime.now()
    logger.info("📡 Starting demo data seeding (no reset)...")
    
    try:
        # Run seeding
        await seed_database()
        
        # Validate
        validation_passed = await validate_demo_environment()
        
        duration = datetime.now() - start_time
        
        if validation_passed:
            logger.info(f"✅ Demo data seeding completed successfully in {duration}")
        else:
            logger.warning("⚠️ Seeding completed but validation found issues")
            
        return validation_passed
        
    except Exception as e:
        logger.error(f"❌ Demo data seeding failed: {e}")
        raise

def main():
    """Main entry point with command line argument handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SigmaSight Demo Database Management")
    parser.add_argument(
        "action", 
        choices=["reset", "seed", "validate"],
        help="Action to perform: reset (DESTRUCTIVE), seed (safe), or validate"
    )
    parser.add_argument(
        "--confirm",
        action="store_true", 
        help="Required for destructive reset operation"
    )
    
    args = parser.parse_args()
    
    if args.action == "reset":
        if not args.confirm:
            logger.error("❌ Reset operation requires --confirm flag for safety")
            logger.error("Usage: python scripts/reset_and_seed.py reset --confirm")
            sys.exit(1)
            
        logger.warning("⚠️ DESTRUCTIVE RESET OPERATION CONFIRMED")
        asyncio.run(reset_and_seed())
        
    elif args.action == "seed":
        logger.info("🌱 Running safe demo data seeding...")
        asyncio.run(seed_only())
        
    elif args.action == "validate":
        logger.info("🔍 Validating demo environment...")
        async def run_validation():
            async with get_async_session() as db:
                return await validate_demo_environment()
        result = asyncio.run(run_validation())
        sys.exit(0 if result else 1)

if __name__ == "__main__":
    main()