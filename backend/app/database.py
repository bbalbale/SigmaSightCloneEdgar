"""
Database configuration and session management for SigmaSight Backend
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import settings
from app.core.logging import db_logger

# Database engine with optimized connection pool
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=20,        # Increased from default 5
    max_overflow=20,     # Increased from default 10
    pool_timeout=30,     # Default 30s wait for connection
    pool_recycle=1800,   # Recycle connections every 30 min
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents greenlet errors in async contexts
)

# Base class for models
class Base(DeclarativeBase):
    """Base class for all database models"""
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )


# Enhanced dependency for getting database session (FastAPI compatible)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session with proper error handling
    """
    async with AsyncSessionLocal() as session:
        try:
            db_logger.debug("Database session created")
            yield session
        except Exception as e:
            db_logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            db_logger.debug("Database session closed")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions (for scripts and batch jobs)
    """
    async with AsyncSessionLocal() as session:
        try:
            db_logger.debug("Async database session created")
            yield session
        except Exception as e:
            db_logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            db_logger.debug("Async database session closed")


async def init_db():
    """
    Initialize database (create tables if needed)
    """
    async with engine.begin() as conn:
        db_logger.info("Initializing database...")
        # Import all models to register them
        from app.models.users import User, Portfolio
        from app.models.positions import Position, Tag
        from app.models.market_data import MarketDataCache, PositionGreeks, FactorDefinition, FactorExposure
        from app.models.snapshots import PortfolioSnapshot, BatchJob, BatchJobSchedule
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        db_logger.info("Database initialization completed")


async def close_db():
    """
    Close database connections
    """
    await engine.dispose()
    db_logger.info("Database connections closed")


# Database connection test
async def test_db_connection():
    """Test database connection"""
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
