"""
Unit tests for InviteCodeService

Tests invite code validation logic including:
- Valid code acceptance
- Invalid code rejection
- Case insensitive matching
- Whitespace handling
"""
import pytest
from app.services.invite_code_service import InviteCodeService
from app.config import settings


class TestInviteCodeService:
    """Test suite for InviteCodeService"""

    def test_valid_code_exact_match(self):
        """Test that exact match of master code is accepted"""
        service = InviteCodeService()
        master_code = settings.BETA_INVITE_CODE

        assert service.validate_invite_code(master_code) is True

    def test_valid_code_case_insensitive(self):
        """Test that code validation is case insensitive"""
        service = InviteCodeService()
        master_code = settings.BETA_INVITE_CODE

        # Test all lowercase
        assert service.validate_invite_code(master_code.lower()) is True

        # Test all uppercase
        assert service.validate_invite_code(master_code.upper()) is True

        # Test mixed case
        assert service.validate_invite_code(master_code.swapcase()) is True

    def test_valid_code_with_whitespace(self):
        """Test that leading/trailing whitespace is handled"""
        service = InviteCodeService()
        master_code = settings.BETA_INVITE_CODE

        # Leading whitespace
        assert service.validate_invite_code(f"  {master_code}") is True

        # Trailing whitespace
        assert service.validate_invite_code(f"{master_code}  ") is True

        # Both
        assert service.validate_invite_code(f"  {master_code}  ") is True

    def test_invalid_code_completely_wrong(self):
        """Test that completely wrong code is rejected"""
        service = InviteCodeService()

        assert service.validate_invite_code("WRONG-CODE-HERE") is False

    def test_invalid_code_partial_match(self):
        """Test that partial matches are rejected"""
        service = InviteCodeService()
        master_code = settings.BETA_INVITE_CODE

        # First word only
        first_word = master_code.split("-")[0]
        assert service.validate_invite_code(first_word) is False

        # Missing last word
        partial = "-".join(master_code.split("-")[:-1])
        assert service.validate_invite_code(partial) is False

    def test_invalid_code_empty_string(self):
        """Test that empty string is rejected"""
        service = InviteCodeService()

        assert service.validate_invite_code("") is False

    def test_invalid_code_whitespace_only(self):
        """Test that whitespace-only string is rejected"""
        service = InviteCodeService()

        assert service.validate_invite_code("   ") is False

    def test_invalid_code_none(self):
        """Test that None value is rejected"""
        service = InviteCodeService()

        # This should not raise an exception
        assert service.validate_invite_code(None) is False

    def test_get_master_invite_code(self):
        """Test that get_master_invite_code returns the config value"""
        service = InviteCodeService()

        master_code = service.get_master_invite_code()
        assert master_code == settings.BETA_INVITE_CODE
        assert len(master_code) > 0
