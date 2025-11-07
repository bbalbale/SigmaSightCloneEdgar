"""
Integration tests for Onboarding API endpoints

Tests the complete onboarding flow:
- User registration
- Login
- CSV template download
- Portfolio creation
- Calculate trigger

Note: These tests use the actual PostgreSQL database running in Docker.
Test data is cleaned up after each test.
"""
import pytest
import pytest_asyncio
import io
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from app.main import app
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.config import settings


@pytest.fixture(scope="function")
def client():
    """Create test client using the actual database"""
    with TestClient(app) as test_client:
        yield test_client

    # Cleanup after test
    import asyncio
    asyncio.run(_cleanup_test_users())


async def _cleanup_test_users():
    """Helper to clean up test users"""
    async with AsyncSessionLocal() as db:
        # Delete test users (cascade will handle portfolios and positions)
        test_emails = [
            "newuser@example.com",
            "testuser@example.com",
            "otheruser@example.com",
            "user@example.com",
            "duplicate@example.com"
        ]

        for email in test_emails:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                await db.delete(user)

        await db.commit()


class TestRegistrationEndpoint:
    """Test POST /api/v1/onboarding/register"""

    def test_valid_registration_succeeds(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "New User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "next_step" in data

    def test_invalid_invite_code_rejected(self, client):
        """Test that invalid invite code returns 401"""
        response = client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "user@example.com",
                "password": "SecurePass123",
                "full_name": "Test User",
                "invite_code": "INVALID-CODE"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "ERR_INVITE_001"

    def test_duplicate_email_rejected(self, client):
        """Test that duplicate email returns 409"""
        # Register first user
        client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123",
                "full_name": "First User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        # Try to register again
        response = client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass123",
                "full_name": "Second User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "ERR_USER_001"

    def test_weak_password_rejected(self, client):
        """Test that weak password returns 422"""
        response = client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "user@example.com",
                "password": "weak",  # Too short, no uppercase, no numbers
                "full_name": "Test User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "ERR_USER_003"

    def test_invalid_email_rejected(self, client):
        """Test that invalid email returns 422"""
        response = client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123",
                "full_name": "Test User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        assert response.status_code == 422


class TestCSVTemplateEndpoint:
    """Test GET /api/v1/onboarding/csv-template"""

    def test_csv_template_download(self, client):
        """Test CSV template download"""
        response = client.get("/api/v1/onboarding/csv-template")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "sigmasight_portfolio_template.csv" in response.headers["Content-Disposition"]

        # Check content
        content = response.text
        assert "Symbol,Quantity,Entry Price Per Share" in content
        assert "AAPL" in content  # Should have example

    def test_csv_template_has_cache_headers(self, client):
        """Test that CSV template has cache headers"""
        response = client.get("/api/v1/onboarding/csv-template")

        assert "Cache-Control" in response.headers
        assert "max-age=3600" in response.headers["Cache-Control"]


class TestCreatePortfolioEndpoint:
    """Test POST /api/v1/onboarding/create-portfolio"""

    def register_and_login(self, client) -> str:
        """Helper to register and login, returns access token"""
        # Register
        client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123",
                "full_name": "Test User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123"
            }
        )

        return login_response.json()["access_token"]

    def test_valid_portfolio_creation_succeeds(self, client, mock_market_data_services):
        """Test successful portfolio creation (mocks external API calls)"""
        token = self.register_and_login(client)

        # Create valid CSV content
        csv_content = """Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,
MSFT,75,380.00,2024-01-20,PUBLIC,STOCK,,,,,,
"""

        # Create portfolio (Phase 2: includes account_name and account_type)
        response = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Test Portfolio",
                "account_name": "Test Taxable Account",
                "account_type": "taxable",
                "equity_balance": "100000",
                "description": "My test portfolio"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "portfolio_id" in data
        assert data["portfolio_name"] == "Test Portfolio"
        assert data["account_name"] == "Test Taxable Account"
        assert data["account_type"] == "taxable"
        assert data["positions_imported"] == 2
        assert data["positions_failed"] == 0

    def test_unauthenticated_request_rejected(self, client):
        """Test that unauthenticated request returns 401"""
        csv_content = "Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share\nAAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,"

        response = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Test Portfolio",
                "account_name": "Test Account",
                "account_type": "taxable",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            }
        )

        assert response.status_code == 401

    def test_duplicate_account_name_rejected(self, client):
        """Test that duplicate account_name is rejected (Phase 2)"""
        token = self.register_and_login(client)

        csv_content = "Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share\nAAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,"

        # Create first portfolio
        client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "First Portfolio",
                "account_name": "My Taxable Account",
                "account_type": "taxable",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Try to create second portfolio with SAME account_name (should fail)
        response = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Second Portfolio",
                "account_name": "My Taxable Account",  # Duplicate account_name
                "account_type": "ira",
                "equity_balance": "200000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "ERR_PORT_001"
        assert "account name" in data["error"]["message"].lower()

    def test_multiple_portfolios_allowed(self, client, mock_market_data_services):
        """Test that users can create multiple portfolios with different account_names (Phase 2)"""
        token = self.register_and_login(client)

        csv_content = "Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share\nAAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,"

        # Create first portfolio (taxable)
        response1 = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "My Trading Account",
                "account_name": "Schwab Taxable",
                "account_type": "taxable",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Create second portfolio (IRA) - should succeed
        response2 = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Retirement Fund",
                "account_name": "Fidelity IRA",
                "account_type": "ira",
                "equity_balance": "250000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Create third portfolio (401k) - should succeed
        response3 = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Employer Plan",
                "account_name": "Company 401k",
                "account_type": "401k",
                "equity_balance": "150000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # All three should succeed
        assert response1.status_code == 201
        assert response2.status_code == 201
        assert response3.status_code == 201

        # Each should have unique portfolio_id
        portfolio_ids = [
            response1.json()["portfolio_id"],
            response2.json()["portfolio_id"],
            response3.json()["portfolio_id"]
        ]
        assert len(set(portfolio_ids)) == 3  # All unique

    def test_invalid_csv_rejected(self, client):
        """Test that invalid CSV returns validation errors"""
        token = self.register_and_login(client)

        # CSV with missing required field (quantity)
        csv_content = "Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share\nAAPL,,158.00,2024-01-15,PUBLIC,STOCK,,,,,,"

        response = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Test Portfolio",
                "account_name": "Test Account",
                "account_type": "taxable",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "ERR_PORT_008"

    def test_uuid_collision_prevention(self, client, mock_market_data_services):
        """
        Test that same portfolio_name with different account_name produces different UUIDs.

        This is a critical test for Phase 2 UUID strategy:
        - UUIDs are generated using (user_id, account_name) not (user_id, portfolio_name)
        - This allows users to have multiple portfolios with the same display name
        - For example: "Retirement" for both IRA and 401k accounts
        """
        token = self.register_and_login(client)

        csv_content = "Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share\nAAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,"

        # Create first portfolio with name "Retirement" and account "IRA Account"
        response1 = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Retirement",  # Same portfolio_name
                "account_name": "IRA Account",    # Different account_name
                "account_type": "ira",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Create second portfolio with same name "Retirement" but different account "401k Account"
        response2 = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Retirement",  # Same portfolio_name
                "account_name": "401k Account",   # Different account_name
                "account_type": "401k",
                "equity_balance": "200000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Both should succeed
        assert response1.status_code == 201
        assert response2.status_code == 201

        # Extract portfolio IDs
        portfolio_id1 = response1.json()["portfolio_id"]
        portfolio_id2 = response2.json()["portfolio_id"]

        # CRITICAL: Portfolio IDs must be different despite same portfolio_name
        assert portfolio_id1 != portfolio_id2, (
            f"UUID collision detected! Same portfolio_name 'Retirement' with different "
            f"account_names should produce different UUIDs. Got: {portfolio_id1} and {portfolio_id2}"
        )

        # Verify both portfolios have the correct metadata
        data1 = response1.json()
        data2 = response2.json()

        assert data1["portfolio_name"] == "Retirement"
        assert data1["account_name"] == "IRA Account"
        assert data1["account_type"] == "ira"

        assert data2["portfolio_name"] == "Retirement"
        assert data2["account_name"] == "401k Account"
        assert data2["account_type"] == "401k"


class TestCalculateEndpoint:
    """Test POST /api/v1/portfolio/{portfolio_id}/calculate"""

    def register_login_create_portfolio(self, client) -> tuple[str, str]:
        """Helper to complete onboarding flow, returns (token, portfolio_id)"""
        # Register
        client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123",
                "full_name": "Test User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPass123"
            }
        )
        token = login_response.json()["access_token"]

        # Create portfolio (Phase 2: includes account_name and account_type)
        csv_content = """Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,
MSFT,75,380.00,2024-01-20,PUBLIC,STOCK,,,,,,
"""
        portfolio_response = client.post(
            "/api/v1/onboarding/create-portfolio",
            data={
                "portfolio_name": "Test Portfolio",
                "account_name": "Test Account",
                "account_type": "taxable",
                "equity_balance": "100000"
            },
            files={
                "csv_file": ("positions.csv", io.BytesIO(csv_content.encode()), "text/csv")
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        portfolio_id = portfolio_response.json()["portfolio_id"]
        return token, portfolio_id

    def test_valid_calculate_request_succeeds(self, client, mock_preprocessing_service, mock_batch_orchestrator):
        """Test successful calculate trigger (mocks preprocessing and batch)"""
        token, portfolio_id = self.register_login_create_portfolio(client)

        response = client.post(
            f"/api/v1/portfolio/{portfolio_id}/calculate",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "started"
        assert "batch_run_id" in data
        assert data["portfolio_id"] == portfolio_id
        assert "preprocessing" in data
        assert "message" in data

    def test_unauthenticated_calculate_rejected(self, client):
        """Test that unauthenticated request returns 401"""
        token, portfolio_id = self.register_login_create_portfolio(client)

        # Try without token
        response = client.post(f"/api/v1/portfolio/{portfolio_id}/calculate")

        assert response.status_code == 401

    def test_wrong_user_calculate_rejected(self, client):
        """Test that user cannot trigger calculations for another user's portfolio"""
        # Create first user and portfolio
        token1, portfolio_id1 = self.register_login_create_portfolio(client)

        # Create second user
        client.post(
            "/api/v1/onboarding/register",
            json={
                "email": "otheruser@example.com",
                "password": "OtherPass123",
                "full_name": "Other User",
                "invite_code": settings.BETA_INVITE_CODE
            }
        )

        # Login as second user
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "otheruser@example.com",
                "password": "OtherPass123"
            }
        )
        token2 = login_response.json()["access_token"]

        # Try to trigger calculations on first user's portfolio
        response = client.post(
            f"/api/v1/portfolio/{portfolio_id1}/calculate",
            headers={"Authorization": f"Bearer {token2}"}
        )

        assert response.status_code == 403

    def test_invalid_portfolio_id_rejected(self, client):
        """Test that invalid portfolio ID returns 404"""
        token, _ = self.register_login_create_portfolio(client)

        # Use invalid UUID
        invalid_id = "00000000-0000-0000-0000-000000000000"

        response = client.post(
            f"/api/v1/portfolio/{invalid_id}/calculate",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    def test_force_parameter_works(self, client):
        """Test that force=true parameter is accepted"""
        token, portfolio_id = self.register_login_create_portfolio(client)

        response = client.post(
            f"/api/v1/portfolio/{portfolio_id}/calculate?force=true",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "started"
