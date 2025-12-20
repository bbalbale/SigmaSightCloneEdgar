"""
Database configuration and session management for SigmaSight Backend

Dual Database Architecture:
- Core DB: portfolios, positions, calculations, market data, chat (high throughput)
- AI DB: RAG documents, memories, feedback with pgvector (heavy/slow queries)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import settings
from app.core.logging import db_logger


# =============================================================================
# Core Database Engine (portfolios, positions, market data, chat)
# =============================================================================
core_engine = create_async_engine(
    settings.core_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=20,        # High throughput for core operations
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,   # Recycle connections every 30 min
)

# Core session factory
CoreSessionLocal = async_sessionmaker(
    core_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =============================================================================
# AI Database Engine (RAG, memories, feedback with pgvector)
# =============================================================================
ai_engine = create_async_engine(
    settings.ai_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,         # Lower throughput for heavy AI queries
    max_overflow=10,
    pool_timeout=60,     # Longer timeout for vector searches
    pool_recycle=1800,
)

# AI session factory
AISessionLocal = async_sessionmaker(
    ai_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =============================================================================
# Base Classes for Models
# =============================================================================
class Base(DeclarativeBase):
    """Base class for Core database models"""
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )


# Note: AiBase is defined in app/models/ai_models.py to avoid circular imports


# =============================================================================
# Core Database Session Management
# =============================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get Core database session with proper error handling
    """
    async with CoreSessionLocal() as session:
        try:
            db_logger.debug("Core database session created")
            yield session
        except Exception as e:
            db_logger.error(f"Core database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            db_logger.debug("Core database session closed")


@asynccontextmanager
async def get_core_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for Core database sessions (for scripts and batch jobs)
    """
    async with CoreSessionLocal() as session:
        try:
            db_logger.debug("Core async session created")
            yield session
        except Exception as e:
            db_logger.error(f"Core async session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            db_logger.debug("Core async session closed")


# =============================================================================
# AI Database Session Management
# =============================================================================
async def get_ai_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get AI database session with proper error handling
    """
    async with AISessionLocal() as session:
        try:
            db_logger.debug("AI database session created")
            yield session
        except Exception as e:
            db_logger.error(f"AI database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            db_logger.debug("AI database session closed")


@asynccontextmanager
async def get_ai_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for AI database sessions (for RAG, memories, feedback)
    """
    async with AISessionLocal() as session:
        try:
            db_logger.debug("AI async session created")
            yield session
        except Exception as e:
            db_logger.error(f"AI async session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
            db_logger.debug("AI async session closed")


# =============================================================================
# Backwards Compatibility Aliases
# =============================================================================
# These maintain compatibility with existing code that uses the old names
engine = core_engine
AsyncSessionLocal = CoreSessionLocal
get_async_session = get_core_session


# =============================================================================
# Database Lifecycle Management
# =============================================================================
async def init_db():
    """
    Initialize database (create tables if needed)
    """
    async with core_engine.begin() as conn:
        db_logger.info("Initializing Core database...")
        # Import all models to register them
        from app.models.users import User, Portfolio
        from app.models.positions import Position, Tag
        from app.models.market_data import MarketDataCache, PositionGreeks, FactorDefinition, FactorExposure
        from app.models.snapshots import PortfolioSnapshot, BatchJob, BatchJobSchedule

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        db_logger.info("Core database initialization completed")

    # AI database tables are created via Alembic migrations (alembic_ai.ini)
    # They require pgvector extension which is handled by the migration


async def close_db():
    """
    Close all database connections
    """
    await core_engine.dispose()
    await ai_engine.dispose()
    db_logger.info("All database connections closed")


async def test_db_connection():
    """Test Core database connection"""
    try:
        async with core_engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Core database connection failed: {e}")
        return False


async def test_ai_db_connection():
    """Test AI database connection"""
    try:
        async with ai_engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"AI database connection failed: {e}")
        return False
