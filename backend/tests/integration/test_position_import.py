"""
Integration tests for PositionImportService via API

These tests verify that import_positions() correctly persists data to PostgreSQL
by testing through the actual API endpoints that the frontend will use.

CRITICAL: These tests would have caught the abs(quantity) bug from code review issue #1.

Requirements:
- PostgreSQL running in Docker (docker-compose up -d)
- Real database (cleanup happens automatically via client fixture)

Approach: Uses httpx.AsyncClient to test the complete async flow:
1. Register user via API
2. Login to get JWT token
3. Create portfolio with CSV via API (calls import_positions internally)
4. Query database to verify positions persisted correctly
"""
import pytest
import pytest_asyncio
import io
from decimal import Decimal
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

import httpx
from app.main import app
from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from app.models.users import User
from app.config import settings


@pytest_asyncio.fixture(scope="function")
async def client():
    """Create async test client using the actual database"""
    from httpx import ASGITransport
    from app.database import get_async_session as original_get_async_session

    # Override dependency to ensure it works correctly in test context
    async def get_test_session():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[original_get_async_session] = get_test_session

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    # Clear overrides
    app.dependency_overrides.clear()

    # Cleanup after test
    await _cleanup_test_users()


async def _cleanup_test_users():
    """Helper to clean up test users"""
    # Use synchronous deletion to avoid ORM relationship issues
    from sqlalchemy import create_engine, delete, select
    from sqlalchemy.orm import Session
    from app.models.users import Portfolio

    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
    engine = create_engine(sync_db_url)

    test_emails = [
        "test_signed_quantity@example.com",
        "test_option_fields@example.com",
        "test_deterministic_uuid@example.com",
    ]

    try:
        with Session(engine) as db:
            # Get user IDs first
            result = db.execute(select(User.id).where(User.email.in_(test_emails)))
            user_ids = [row[0] for row in result.fetchall()]

            if user_ids:
                # Get portfolio IDs for these users
                result = db.execute(select(Portfolio.id).where(Portfolio.user_id.in_(user_ids)))
                portfolio_ids = [row[0] for row in result.fetchall()]

                if portfolio_ids:
                    # Delete positions first
                    db.execute(delete(Position).where(Position.portfolio_id.in_(portfolio_ids)))
                    # Delete portfolios
                    db.execute(delete(Portfolio).where(Portfolio.id.in_(portfolio_ids)))

                # Delete users
                db.execute(delete(User).where(User.id.in_(user_ids)))
                db.commit()
    except Exception as e:
        # Ignore cleanup errors
        pass


class TestPositionImportViaAPI:
    """
    CRITICAL: Test that import_positions() preserves signed quantities via API.

    These tests use httpx.AsyncClient to test the complete flow:
    - Register user → Login → Create portfolio with CSV → Verify database

    This approach tests the actual code path that the frontend will use.
    """

    async def register_and_login(self, client, email: str) -> str:
        """Helper to register and login, returns access token"""
        # Register
        await client.post(
            "/api/v1/onboarding/register",
            json={
                "email": email,
                "password": "TestPass123",
                "full_name": "Test User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "TestPass123"
            }
        )

        return login_response.json()["access_token"]

    @pytest.mark.asyncio
    async def test_import_positions_preserves_signed_quantity(self, client, mock_market_data_services):
        """
        CRITICAL: Verify short position quantities stay negative via API.

        This test would have caught the abs(quantity) bug from code review issue #1.

        Flow:
        1. Register user and login via API
        2. Create portfolio with CSV containing negative quantities via API
        3. Query database to verify Position.quantity stayed negative
        4. Cleanup happens automatically via fixture
        """
        # Step 1: Register and login
        token = await self.register_and_login(client, "test_signed_quantity@example.com")

        # Step 2: Create CSV with mixed long/short positions
        csv_content = """Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,
SHOP,-25,62.50,2024-02-10,PUBLIC,STOCK,,,,,,
QQQ,-15,6.20,2024-02-01,OPTIONS,,QQQ,420.00,2025-08-15,PUT,,
"""

        # Step 3: Create portfolio via API (calls import_positions internally)
        response = await client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Test Portfolio",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert: Portfolio creation succeeded
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["positions_imported"] == 3
        assert data["positions_failed"] == 0
        portfolio_id = data["portfolio_id"]

        # Step 4: Query database directly to verify signed quantities (using sync connection)
        from sqlalchemy import create_engine
        from app.config import settings

        # Create synchronous engine for verification
        sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
        engine = create_engine(sync_db_url)

        from sqlalchemy.orm import Session
        with Session(engine) as db:
            positions = db.execute(
                select(Position).where(Position.portfolio_id == portfolio_id)
            ).scalars().all()

            assert len(positions) == 3, f"Expected 3 positions, found {len(positions)}"

            # Find each position
            aapl = next((p for p in positions if p.symbol == "AAPL"), None)
            shop = next((p for p in positions if p.symbol == "SHOP"), None)
            qqq = next((p for p in positions if "QQQ" in p.symbol), None)

            assert aapl is not None, "AAPL position not found"
            assert shop is not None, "SHOP position not found"
            assert qqq is not None, "QQQ position not found"

            # CRITICAL: Verify signed quantities preserved in PostgreSQL
            assert aapl.quantity == Decimal("100"), f"Long AAPL quantity should be 100, got {aapl.quantity}"
            assert shop.quantity == Decimal("-25"), f"Short SHOP quantity MUST be -25, got {shop.quantity}"
            assert qqq.quantity == Decimal("-15"), f"Short QQQ quantity MUST be -15, got {qqq.quantity}"

            # Verify position types
            assert aapl.position_type == PositionType.LONG, f"AAPL should be LONG, got {aapl.position_type}"
            assert shop.position_type == PositionType.SHORT, f"SHOP should be SHORT, got {shop.position_type}"
            assert qqq.position_type == PositionType.SP, f"QQQ should be SP (Short Put), got {qqq.position_type}"

    @pytest.mark.asyncio
    async def test_import_positions_maps_option_fields(self, client, mock_market_data_services):
        """
        Verify option fields are correctly mapped to PostgreSQL via API.

        Tests:
        - underlying_symbol
        - strike_price (Numeric type in PostgreSQL)
        - expiration_date (string → date conversion)
        - option_type (stored in position_type enum)
        """
        # Step 1: Register and login
        token = await self.register_and_login(client, "test_option_fields@example.com")

        # Step 2: Create CSV with option position
        csv_content = """Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
SPY,10,5.50,2024-02-01,OPTIONS,,SPY,450.00,2025-03-15,CALL,,
"""

        # Step 3: Create portfolio via API
        response = await client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Options Test Portfolio",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert: Portfolio creation succeeded
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["positions_imported"] == 1
        portfolio_id = data["portfolio_id"]

        # Step 4: Query database to verify option fields (using sync connection)
        from sqlalchemy import create_engine
        from app.config import settings
        from datetime import date

        # Create synchronous engine for verification
        sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
        engine = create_engine(sync_db_url)

        from sqlalchemy.orm import Session
        with Session(engine) as db:
            position = db.execute(
                select(Position).where(Position.portfolio_id == portfolio_id)
            ).scalar_one()

            # Verify option fields mapped correctly in PostgreSQL
            assert position.underlying_symbol == "SPY", f"Expected SPY, got {position.underlying_symbol}"
            assert position.strike_price == Decimal("450.00"), f"Expected 450.00, got {position.strike_price}"
            assert position.expiration_date == date(2025, 3, 15), f"Expected 2025-03-15, got {position.expiration_date}"
            assert position.position_type == PositionType.LC, f"Expected LC (Long Call), got {position.position_type}"
            assert position.investment_class == "OPTIONS", f"Expected OPTIONS, got {position.investment_class}"
            assert position.quantity == Decimal("10"), f"Expected 10, got {position.quantity}"

    @pytest.mark.asyncio
    async def test_duplicate_positions_in_csv_handled_correctly(self, client, mock_market_data_services):
        """
        Verify that duplicate positions in CSV are detected and reported.

        This tests the deduplication logic that would prevent issues when users
        accidentally include the same position twice in their CSV.
        """
        # Step 1: Register and login
        token = await self.register_and_login(client, "test_deterministic_uuid@example.com")

        # Step 2: Create CSV with duplicate position (same symbol + entry date)
        csv_content = """Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
TSLA,50,185.00,2024-01-15,PUBLIC,STOCK,,,,,,
MSFT,100,380.00,2024-01-20,PUBLIC,STOCK,,,,,,
TSLA,50,185.00,2024-01-15,PUBLIC,STOCK,,,,,,
"""

        # Step 3: Create portfolio via API
        response = await client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Duplicate Test Portfolio",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Assert: Portfolio creation should fail with validation error for duplicate
        assert response.status_code == 400, f"Expected 400 for duplicate positions, got {response.status_code}"
        data = response.json()

        # The error should mention duplicate
        error_code = data.get("error", {}).get("code")
        assert error_code == "ERR_PORT_008", f"Expected ERR_PORT_008 (CSV validation failed), got {error_code}"

        # Verify error details mention the duplicate
        validation_errors = data.get("error", {}).get("validation_errors", [])
        duplicate_errors = [e for e in validation_errors if "ERR_POS_023" in e.get("error_code", "")]
        assert len(duplicate_errors) > 0, "Expected duplicate position error (ERR_POS_023)"
