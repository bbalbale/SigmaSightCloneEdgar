"""
Invite Code Service

Validates user invite codes for beta registration.

Current implementation uses a single master invite code from configuration.
Future enhancements (Phase 3+) may include:
- Database-backed invite codes
- Usage tracking
- Expiration dates
- Cohort-specific codes
"""
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class InviteCodeService:
    """
    Service for validating invite codes.

    Phase 1 implementation uses a single master code from configuration
    for simplicity and ease of deployment.
    """

    @staticmethod
    def validate_invite_code(code: str) -> bool:
        """
        Validate an invite code.

        Performs case-insensitive comparison with the configured master code.
        Whitespace is trimmed from input.

        Args:
            code: Invite code to validate

        Returns:
            True if code is valid, False otherwise

        Examples:
            >>> service = InviteCodeService()
            >>> service.validate_invite_code("PRESCOTT-LINNAEAN-COWPERTHWAITE")
            True
            >>> service.validate_invite_code("prescott-linnaean-cowperthwaite")
            True  # Case insensitive
            >>> service.validate_invite_code("  PRESCOTT-LINNAEAN-COWPERTHWAITE  ")
            True  # Whitespace trimmed
            >>> service.validate_invite_code("INVALID-CODE")
            False
        """
        if not code:
            logger.debug("Empty invite code provided")
            return False

        # Normalize code: strip whitespace and convert to uppercase
        code_normalized = code.strip().upper()
        master_code_normalized = settings.BETA_INVITE_CODE.strip().upper()

        # Case-insensitive comparison
        is_valid = code_normalized == master_code_normalized

        if is_valid:
            logger.info(f"Valid invite code validated")
        else:
            logger.warning(f"Invalid invite code attempt")

        return is_valid

    @staticmethod
    def get_master_invite_code() -> str:
        """
        Get the current master invite code.

        This method is primarily for testing and admin purposes.
        In production, the master code should not be exposed to clients.

        Returns:
            Current master invite code from configuration

        Note:
            This method is useful for:
            - Testing invite code validation
            - Admin tools that need to display the code
            - Documentation/help endpoints
        """
        return settings.BETA_INVITE_CODE


# Convenience instance for direct use
invite_code_service = InviteCodeService()
