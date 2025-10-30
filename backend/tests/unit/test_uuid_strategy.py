"""
Unit tests for UUIDStrategy

Tests UUID generation logic including:
- Deterministic UUID generation
- Random UUID generation
- Demo user detection
- UUID consistency
"""
import pytest
from uuid import UUID
from app.core.uuid_strategy import UUIDStrategy
from app.config import settings


class TestUUIDStrategy:
    """Test suite for UUIDStrategy"""

    def test_demo_user_always_deterministic(self):
        """Test that demo users always get deterministic UUIDs"""
        demo_email = "test@sigmasight.com"

        # Generate UUID twice
        uuid1 = UUIDStrategy.generate_user_uuid(demo_email)
        uuid2 = UUIDStrategy.generate_user_uuid(demo_email)

        # Should be identical
        assert uuid1 == uuid2
        assert isinstance(uuid1, UUID)

    def test_demo_user_different_emails_different_uuids(self):
        """Test that different demo emails get different UUIDs"""
        email1 = "user1@sigmasight.com"
        email2 = "user2@sigmasight.com"

        uuid1 = UUIDStrategy.generate_user_uuid(email1)
        uuid2 = UUIDStrategy.generate_user_uuid(email2)

        assert uuid1 != uuid2

    def test_deterministic_uuid_consistency(self):
        """Test that deterministic UUIDs are consistent"""
        email = "user@example.com"

        # Generate with deterministic=True
        uuid1 = UUIDStrategy.generate_user_uuid(email, use_deterministic=True)
        uuid2 = UUIDStrategy.generate_user_uuid(email, use_deterministic=True)

        assert uuid1 == uuid2

    def test_random_uuid_uniqueness(self):
        """Test that random UUIDs are unique"""
        email = "user@example.com"

        # Generate with deterministic=False
        uuid1 = UUIDStrategy.generate_user_uuid(email, use_deterministic=False)
        uuid2 = UUIDStrategy.generate_user_uuid(email, use_deterministic=False)

        # Should be different (random)
        assert uuid1 != uuid2

    def test_email_normalization(self):
        """Test that emails are normalized (case, whitespace)"""
        # Test case sensitivity
        uuid1 = UUIDStrategy.generate_user_uuid("user@example.com", use_deterministic=True)
        uuid2 = UUIDStrategy.generate_user_uuid("USER@EXAMPLE.COM", use_deterministic=True)
        uuid3 = UUIDStrategy.generate_user_uuid("User@Example.Com", use_deterministic=True)

        assert uuid1 == uuid2 == uuid3

        # Test whitespace
        uuid4 = UUIDStrategy.generate_user_uuid("  user@example.com  ", use_deterministic=True)
        assert uuid1 == uuid4

    def test_portfolio_uuid_deterministic(self):
        """Test portfolio UUID generation (deterministic)"""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        portfolio_name = "My Portfolio"

        # Generate twice
        uuid1 = UUIDStrategy.generate_portfolio_uuid(user_id, portfolio_name, use_deterministic=True)
        uuid2 = UUIDStrategy.generate_portfolio_uuid(user_id, portfolio_name, use_deterministic=True)

        assert uuid1 == uuid2
        assert isinstance(uuid1, UUID)

    def test_portfolio_uuid_random(self):
        """Test portfolio UUID generation (random)"""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        portfolio_name = "My Portfolio"

        # Generate twice
        uuid1 = UUIDStrategy.generate_portfolio_uuid(user_id, portfolio_name, use_deterministic=False)
        uuid2 = UUIDStrategy.generate_portfolio_uuid(user_id, portfolio_name, use_deterministic=False)

        # Should be different (random)
        assert uuid1 != uuid2

    def test_portfolio_name_normalization(self):
        """Test that portfolio names are normalized"""
        user_id = UUID("12345678-1234-5678-1234-567812345678")

        uuid1 = UUIDStrategy.generate_portfolio_uuid(user_id, "My Portfolio", use_deterministic=True)
        uuid2 = UUIDStrategy.generate_portfolio_uuid(user_id, "  My Portfolio  ", use_deterministic=True)

        assert uuid1 == uuid2

    def test_position_uuid_deterministic(self):
        """Test position UUID generation (deterministic)"""
        portfolio_id = UUID("12345678-1234-5678-1234-567812345678")
        symbol = "AAPL"
        entry_date = "2024-01-15"

        # Generate twice
        uuid1 = UUIDStrategy.generate_position_uuid(portfolio_id, symbol, entry_date, use_deterministic=True)
        uuid2 = UUIDStrategy.generate_position_uuid(portfolio_id, symbol, entry_date, use_deterministic=True)

        assert uuid1 == uuid2
        assert isinstance(uuid1, UUID)

    def test_position_uuid_symbol_normalization(self):
        """Test that position symbols are normalized"""
        portfolio_id = UUID("12345678-1234-5678-1234-567812345678")
        entry_date = "2024-01-15"

        # Test case normalization
        uuid1 = UUIDStrategy.generate_position_uuid(portfolio_id, "AAPL", entry_date, use_deterministic=True)
        uuid2 = UUIDStrategy.generate_position_uuid(portfolio_id, "aapl", entry_date, use_deterministic=True)
        uuid3 = UUIDStrategy.generate_position_uuid(portfolio_id, "  AAPL  ", entry_date, use_deterministic=True)

        assert uuid1 == uuid2 == uuid3

    def test_config_based_uuid_generation(self):
        """Test that config setting controls UUID strategy"""
        email = "user@example.com"

        # Generate using default config setting
        uuid1 = UUIDStrategy.generate_user_uuid(email)
        uuid2 = UUIDStrategy.generate_user_uuid(email)

        # If DETERMINISTIC_UUIDS is True (Phase 1), should be same
        # If False (Phase 3), would be different
        if settings.DETERMINISTIC_UUIDS:
            assert uuid1 == uuid2
        else:
            # This test would pass in Phase 3
            pass

    def test_different_users_different_uuids(self):
        """Test that different users get different UUIDs"""
        uuid1 = UUIDStrategy.generate_user_uuid("user1@example.com", use_deterministic=True)
        uuid2 = UUIDStrategy.generate_user_uuid("user2@example.com", use_deterministic=True)

        assert uuid1 != uuid2

    def test_different_portfolios_different_uuids(self):
        """Test that different portfolios get different UUIDs"""
        user_id = UUID("12345678-1234-5678-1234-567812345678")

        uuid1 = UUIDStrategy.generate_portfolio_uuid(user_id, "Portfolio A", use_deterministic=True)
        uuid2 = UUIDStrategy.generate_portfolio_uuid(user_id, "Portfolio B", use_deterministic=True)

        assert uuid1 != uuid2

    def test_different_positions_different_uuids(self):
        """Test that different positions get different UUIDs"""
        portfolio_id = UUID("12345678-1234-5678-1234-567812345678")
        entry_date = "2024-01-15"

        # Different symbols
        uuid1 = UUIDStrategy.generate_position_uuid(portfolio_id, "AAPL", entry_date, use_deterministic=True)
        uuid2 = UUIDStrategy.generate_position_uuid(portfolio_id, "MSFT", entry_date, use_deterministic=True)

        assert uuid1 != uuid2

        # Different dates
        uuid3 = UUIDStrategy.generate_position_uuid(portfolio_id, "AAPL", "2024-01-15", use_deterministic=True)
        uuid4 = UUIDStrategy.generate_position_uuid(portfolio_id, "AAPL", "2024-02-15", use_deterministic=True)

        assert uuid3 != uuid4
