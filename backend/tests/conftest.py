"""
Pytest configuration and fixtures for test suite

Provides:
- Async database session for integration tests
- Test database setup/teardown
- Common test fixtures
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.database import Base
from app.config import settings


# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests"""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create only the tables we need for these tests (not all tables)
    # This avoids SQLite JSONB incompatibility issues
    from app.models.users import User, Portfolio
    from app.models.positions import Position
    from app.models.snapshots import PortfolioSnapshot

    def create_tables(connection):
        """Create tables synchronously"""
        User.__table__.create(connection, checkfirst=True)
        Portfolio.__table__.create(connection, checkfirst=True)
        Position.__table__.create(connection, checkfirst=True)
        PortfolioSnapshot.__table__.create(connection, checkfirst=True)

    def drop_tables(connection):
        """Drop tables synchronously"""
        PortfolioSnapshot.__table__.drop(connection, checkfirst=True)
        Position.__table__.drop(connection, checkfirst=True)
        Portfolio.__table__.drop(connection, checkfirst=True)
        User.__table__.drop(connection, checkfirst=True)

    async with engine.begin() as conn:
        await conn.run_sync(create_tables)

    yield engine

    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(drop_tables)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Create async database session for tests"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()  # Rollback any changes after test
