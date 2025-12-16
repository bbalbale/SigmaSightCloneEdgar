"""
UUID Generation Strategy

Provides flexible UUID generation for users and portfolios with two modes:
1. Deterministic UUIDs (uuid5) - For demo users and Phase 1 testing
2. Random UUIDs (uuid4) - For production users (Phase 3+)

Key Features:
- Demo users (@sigmasight.com) always get deterministic UUIDs
- Config flag controls UUID strategy for non-demo users
- Deterministic UUIDs allow predictable testing and data verification
- Random UUIDs ensure security for production users
"""
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS
from typing import Optional

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class UUIDStrategy:
    """
    UUID generation strategy for users and portfolios.

    Supports both deterministic (uuid5) and random (uuid4) generation
    based on configuration and user type.
    """

    @staticmethod
    def _is_demo_user(email: str) -> bool:
        """
        Check if email is a demo user.

        Demo users (@sigmasight.com) always use deterministic UUIDs
        for consistency across environments.

        Args:
            email: User email address

        Returns:
            True if demo user, False otherwise
        """
        return email.lower().endswith("@sigmasight.com")

    @staticmethod
    def generate_user_uuid(
        email: str,
        use_deterministic: Optional[bool] = None
    ) -> UUID:
        """
        Generate UUID for a user.

        Strategy:
        1. Demo users (@sigmasight.com) → always deterministic
        2. Non-demo users → use config setting or override
        3. Deterministic: uuid5(NAMESPACE_DNS, email)
        4. Random: uuid4()

        Args:
            email: User email address (required)
            use_deterministic: Override config setting (optional)
                              If None, uses settings.DETERMINISTIC_UUIDS

        Returns:
            UUID object

        Examples:
            >>> # Demo user (always deterministic)
            >>> uuid1 = UUIDStrategy.generate_user_uuid("demo@sigmasight.com")
            >>> uuid2 = UUIDStrategy.generate_user_uuid("demo@sigmasight.com")
            >>> assert uuid1 == uuid2  # Always same UUID

            >>> # Production user (config-controlled)
            >>> uuid3 = UUIDStrategy.generate_user_uuid("user@gmail.com")
            >>> # Depends on settings.DETERMINISTIC_UUIDS
        """
        # Normalize email for consistency
        email_normalized = email.lower().strip()

        # Demo users always get deterministic UUIDs
        if UUIDStrategy._is_demo_user(email_normalized):
            logger.debug(f"Generating deterministic UUID for demo user: {email_normalized}")
            return uuid5(NAMESPACE_DNS, email_normalized)

        # Non-demo users: use config or override
        should_be_deterministic = (
            use_deterministic
            if use_deterministic is not None
            else settings.DETERMINISTIC_UUIDS
        )

        if should_be_deterministic:
            logger.debug(f"Generating deterministic UUID for user: {email_normalized}")
            return uuid5(NAMESPACE_DNS, email_normalized)
        else:
            logger.debug(f"Generating random UUID for user: {email_normalized}")
            return uuid4()

    @staticmethod
    def generate_portfolio_uuid(
        user_id: UUID,
        account_name: str,
        use_deterministic: Optional[bool] = None
    ) -> UUID:
        """
        Generate UUID for a portfolio.

        Strategy:
        1. Uses same deterministic/random logic as user UUIDs
        2. Deterministic: uuid5(NAMESPACE_DNS, f"{user_id}:{account_name}")
        3. Random: uuid4()

        Note: Uses account_name (not portfolio_name) to prevent UUID collisions
        when a user has multiple portfolios with the same display name
        (e.g., "Retirement" for both taxable and IRA accounts).

        Args:
            user_id: User's UUID (required)
            account_name: Portfolio account name (required, unique per user)
            use_deterministic: Override config setting (optional)
                              If None, uses settings.DETERMINISTIC_UUIDS

        Returns:
            UUID object

        Examples:
            >>> user_id = UUID("12345678-1234-5678-1234-567812345678")
            >>> uuid1 = UUIDStrategy.generate_portfolio_uuid(user_id, "My Portfolio")
            >>> uuid2 = UUIDStrategy.generate_portfolio_uuid(user_id, "My Portfolio")
            >>> # uuid1 == uuid2 if DETERMINISTIC_UUIDS=True
        """
        # Normalize account name
        account_name_normalized = account_name.strip()

        # Use config or override
        should_be_deterministic = (
            use_deterministic
            if use_deterministic is not None
            else settings.DETERMINISTIC_UUIDS
        )

        if should_be_deterministic:
            # Create deterministic UUID from user_id + account_name
            namespace_string = f"{user_id}:{account_name_normalized}"
            logger.debug(f"Generating deterministic portfolio UUID: {namespace_string}")
            return uuid5(NAMESPACE_DNS, namespace_string)
        else:
            logger.debug("Generating random portfolio UUID")
            return uuid4()

    @staticmethod
    def generate_position_uuid(
        portfolio_id: UUID,
        symbol: str,
        entry_date: str,
        use_deterministic: Optional[bool] = None
    ) -> UUID:
        """
        Generate UUID for a position.

        Strategy:
        1. Uses same deterministic/random logic as other entities
        2. Deterministic: uuid5(NAMESPACE_DNS, f"{portfolio_id}:{symbol}:{entry_date}")
        3. Random: uuid4()

        Args:
            portfolio_id: Portfolio's UUID (required)
            symbol: Position symbol (required)
            entry_date: Entry date as string (YYYY-MM-DD)
            use_deterministic: Override config setting (optional)

        Returns:
            UUID object

        Examples:
            >>> portfolio_id = UUID("12345678-1234-5678-1234-567812345678")
            >>> uuid1 = UUIDStrategy.generate_position_uuid(
            ...     portfolio_id, "AAPL", "2024-01-15"
            ... )
            >>> # Deterministic if DETERMINISTIC_UUIDS=True
        """
        # Normalize symbol
        symbol_normalized = symbol.upper().strip()
        entry_date_normalized = entry_date.strip()

        # Use config or override
        should_be_deterministic = (
            use_deterministic
            if use_deterministic is not None
            else settings.DETERMINISTIC_UUIDS
        )

        if should_be_deterministic:
            # Create deterministic UUID from portfolio_id + symbol + entry_date
            namespace_string = f"{portfolio_id}:{symbol_normalized}:{entry_date_normalized}"
            logger.debug(f"Generating deterministic position UUID: {namespace_string}")
            return uuid5(NAMESPACE_DNS, namespace_string)
        else:
            logger.debug("Generating random position UUID")
            return uuid4()


# Convenience functions for direct use
def generate_user_uuid(email: str, use_deterministic: Optional[bool] = None) -> UUID:
    """Generate UUID for a user. See UUIDStrategy.generate_user_uuid for details."""
    return UUIDStrategy.generate_user_uuid(email, use_deterministic)


def generate_portfolio_uuid(
    user_id: UUID,
    account_name: str,
    use_deterministic: Optional[bool] = None
) -> UUID:
    """Generate UUID for a portfolio. See UUIDStrategy.generate_portfolio_uuid for details."""
    return UUIDStrategy.generate_portfolio_uuid(user_id, account_name, use_deterministic)


def generate_position_uuid(
    portfolio_id: UUID,
    symbol: str,
    entry_date: str,
    use_deterministic: Optional[bool] = None
) -> UUID:
    """Generate UUID for a position. See UUIDStrategy.generate_position_uuid for details."""
    return UUIDStrategy.generate_position_uuid(portfolio_id, symbol, entry_date, use_deterministic)
