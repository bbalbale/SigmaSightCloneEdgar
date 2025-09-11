#!/usr/bin/env python3
"""
Professional Alembic-Based Database Setup for Development
Uses proper database migrations for professional development workflow
"""
import asyncio
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import engine
from app.core.logging import setup_logging, get_logger
from app.config import settings
from sqlalchemy import text

# Setup logging
setup_logging()
logger = get_logger("setup_dev_database_alembic")

async def setup_development_database_with_alembic():
    """
    Set up development database using proper Alembic migrations
    This is the professional approach for database versioning
    """
    try:
        logger.info("🚀 Setting up development database with Alembic...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database URL: {settings.DATABASE_URL}")
        
        if settings.ENVIRONMENT == "production":
            logger.error("❌ This script is for development environments!")
            logger.error("For production, use 'alembic upgrade head' directly")
            sys.exit(1)
        
        # Test database connectivity
        logger.info("🔍 Testing database connectivity...")
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            logger.error("Make sure PostgreSQL is running: docker-compose up -d")
            return False
        
        # Check current migration status
        logger.info("📋 Checking current migration status...")
        try:
            result = subprocess.run(
                [".venv/bin/alembic", "current"], 
                capture_output=True, 
                text=True, 
                cwd=project_root
            )
            if result.returncode == 0:
                current_migration = result.stdout.strip()
                logger.info(f"Current migration: {current_migration}")
            else:
                logger.warning(f"Could not determine current migration: {result.stderr}")
        except Exception as e:
            logger.warning(f"Could not check migration status: {e}")
        
        # Run Alembic upgrade
        logger.info("⬆️  Running Alembic database migrations...")
        try:
            result = subprocess.run(
                [".venv/bin/alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0:
                logger.info("✅ Alembic migrations completed successfully")
                logger.info("Migration output:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            else:
                logger.error("❌ Alembic migrations failed")
                logger.error(f"Error output: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to run Alembic migrations: {e}")
            return False
        
        # Verify database schema
        await verify_database_schema()
        
        logger.info("✅ Development database setup completed with Alembic!")
        print("🎯 Database ready for professional development!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        print(f"❌ Database setup failed: {e}")
        return False

async def verify_database_schema():
    """Verify the database schema is correct"""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Check critical tables exist
            critical_tables = [
                'users', 'portfolios', 'positions', 'market_data_cache',
                'fund_holdings', 'factor_definitions', 'portfolio_snapshots',
                'alembic_version'  # Alembic tracking table
            ]
            
            for table in critical_tables:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """))
                exists = result.scalar()
                if not exists:
                    logger.error(f"❌ Critical table missing: {table}")
                    return False
                    
            # Get total table count
            result = await conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """))
            table_count = result.scalar()
            
            logger.info(f"✅ Database schema verified: {table_count} tables including:")
            for table in critical_tables:
                logger.info(f"  - {table}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False

async def reset_development_database():
    """
    Reset development database (DANGEROUS - only for development!)
    Drops all tables and recreates from migrations
    """
    try:
        logger.warning("⚠️  RESETTING DEVELOPMENT DATABASE - ALL DATA WILL BE LOST!")
        
        # Drop all tables except alembic_version
        logger.info("🔄 Dropping all application tables...")
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Get all table names
            result = await conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename != 'alembic_version';
            """))
            tables = [row[0] for row in result.fetchall()]
            
            # Drop tables with CASCADE to handle foreign keys
            for table in tables:
                await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                logger.info(f"  Dropped table: {table}")
        
        # Reset alembic to base state
        logger.info("🔄 Resetting Alembic to base state...")
        result = subprocess.run(
            [".venv/bin/alembic", "downgrade", "base"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            logger.info("✅ Alembic reset to base")
        else:
            logger.warning(f"Alembic reset warning: {result.stderr}")
        
        # Run migrations from scratch
        logger.info("⬆️  Recreating database from migrations...")
        return await setup_development_database_with_alembic()
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        return False

async def main():
    """Main setup function"""
    print("🏗️  SigmaSight Professional Database Setup (Alembic)")
    print("=" * 60)
    print("This uses proper Alembic migrations for professional development.")
    print()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        print("⚠️  RESET MODE: This will destroy all data!")
        if sys.stdin.isatty():
            if input("Are you sure? Type 'RESET' to confirm: ") != "RESET":
                print("Reset cancelled.")
                return
        else:
            print("Running in non-interactive reset mode...")
        
        success = await reset_development_database()
    else:
        print("Running standard Alembic upgrade...")
        if sys.stdin.isatty():
            if input("Continue with Alembic migrations? (y/N): ").lower() != 'y':
                print("Setup cancelled.")
                return
        else:
            print("Running in non-interactive mode...")
        
        success = await setup_development_database_with_alembic()
    
    if success:
        print("\n🎉 Database setup complete!")
        print("\nNext steps:")
        print("1. Run: uv run python scripts/seed_database.py")
        print("2. Start development: uv run python run.py")
        print("\nFor future schema changes:")
        print("1. Modify models in app/models/")
        print("2. Generate migration: alembic revision --autogenerate -m 'description'")
        print("3. Apply migration: alembic upgrade head")
        print("4. Share migration file with team via git")
    else:
        print("\n❌ Setup failed")
        print("Check the logs above for specific errors")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())