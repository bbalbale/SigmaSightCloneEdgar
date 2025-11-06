"""
Onboarding Service

Main orchestration service for user and portfolio onboarding.

Handles:
1. User Registration
   - Invite code validation
   - Email/password validation
   - User creation with deterministic UUIDs

2. Portfolio Creation with CSV Import
   - Portfolio validation (one per user)
   - CSV parsing and validation
   - Position import
   - Transaction management

This service coordinates all other onboarding services:
- InviteCodeService
- CSVParserService
- PositionImportService
- UUIDStrategy

IMPORTANT: This service does NOT commit transactions.
The caller (request handler) is responsible for transaction management.
"""
import re
from uuid import UUID
from typing import Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import UploadFile

from app.core.logging import get_logger
from app.core.auth import get_password_hash
from app.core.uuid_strategy import generate_user_uuid, generate_portfolio_uuid
from app.models.users import User, Portfolio
from app.services.invite_code_service import invite_code_service
from app.services.csv_parser_service import csv_parser_service
from app.services.position_import_service import position_import_service
from app.core.onboarding_errors import (
    InviteCodeError,
    UserExistsError,
    InvalidEmailError,
    WeakPasswordError,
    InvalidFullNameError,
    PortfolioExistsError,
    InvalidAccountTypeError,
    CSVValidationError,
    create_csv_error,
    format_csv_validation_errors,
    ERR_PORT_002, ERR_PORT_003, ERR_PORT_004, ERR_PORT_005, ERR_PORT_006, ERR_PORT_007, ERR_PORT_008, ERR_PORT_010,
    get_error_message
)

logger = get_logger(__name__)

# Email validation regex (basic)
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Password strength requirements
MIN_PASSWORD_LENGTH = 8
MAX_PORTFOLIO_NAME_LENGTH = 255
MAX_EQUITY_BALANCE = Decimal("1000000000000")  # $1 trillion

# Account types (Phase 2)
ALLOWED_ACCOUNT_TYPES = {'taxable', 'ira', 'roth_ira', '401k', '403b', '529', 'hsa', 'trust', 'other'}


class OnboardingService:
    """Main onboarding orchestration service"""

    @staticmethod
    async def register_user(
        email: str,
        password: str,
        full_name: str,
        invite_code: str,
        db: AsyncSession
    ) -> User:
        """
        Register a new user.

        Validates:
        - Invite code
        - Email format and uniqueness
        - Password strength
        - Full name presence

        IMPORTANT: Does NOT commit - caller manages transaction.

        Args:
            email: User email address
            password: Plain text password
            full_name: User's full name
            invite_code: Beta invite code
            db: Database session

        Returns:
            Created User object

        Raises:
            InviteCodeError: Invalid invite code
            UserExistsError: Email already exists
            InvalidEmailError: Invalid email format
            WeakPasswordError: Password doesn't meet requirements
            InvalidFullNameError: Full name is empty
        """
        # 1. Validate invite code
        if not invite_code_service.validate_invite_code(invite_code):
            logger.warning(f"Invalid invite code attempt for {email}")
            raise InviteCodeError()

        # 2. Validate email format
        email_normalized = email.lower().strip()
        if not re.match(EMAIL_REGEX, email_normalized):
            raise InvalidEmailError(email_normalized)

        # 3. Check if email already exists
        result = await db.execute(
            select(User).where(User.email == email_normalized)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserExistsError(email_normalized)

        # 4. Validate password strength
        if len(password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(details={"reason": "Too short"})

        # Must contain uppercase, lowercase, and number
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            raise WeakPasswordError(details={
                "reason": "Missing required character types",
                "has_uppercase": has_upper,
                "has_lowercase": has_lower,
                "has_digit": has_digit
            })

        # 5. Validate full name
        full_name_normalized = full_name.strip()
        if not full_name_normalized:
            raise InvalidFullNameError()

        # 6. Generate UUID (deterministic for demo users)
        user_uuid = generate_user_uuid(email_normalized)

        # 7. Hash password
        hashed_password = get_password_hash(password)

        # 8. Create User
        user = User(
            id=user_uuid,
            email=email_normalized,
            hashed_password=hashed_password,
            full_name=full_name_normalized,
            is_active=True
        )

        db.add(user)
        await db.flush()  # Flush to get the ID, but don't commit

        logger.info(f"User registered: {email_normalized} (id={user.id})")

        return user

    @staticmethod
    async def create_portfolio_with_csv(
        user_id: UUID,
        portfolio_name: str,
        account_name: str,
        account_type: str,
        equity_balance: Decimal,
        csv_file: UploadFile,
        description: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create portfolio with CSV import.
        Supports multiple portfolios per user (Phase 2).

        Validates:
        - Account type (must be in allowed list)
        - No duplicate account_name for this user
        - Portfolio name
        - Equity balance
        - CSV file structure and content

        Imports:
        - Positions from CSV

        IMPORTANT: Does NOT commit - caller manages transaction.
        Does NOT run preprocessing - that's deferred to calculate endpoint.

        Args:
            user_id: User UUID
            portfolio_name: Portfolio display name
            account_name: Portfolio account name (unique per user)
            account_type: Account type (taxable, ira, roth_ira, 401k, 403b, 529, hsa, trust, other)
            equity_balance: User's account equity balance
            csv_file: Uploaded CSV file
            description: Optional portfolio description
            db: Database session

        Returns:
            Dictionary with portfolio details and import results:
            {
                "portfolio_id": str,
                "portfolio_name": str,
                "account_name": str,
                "account_type": str,
                "positions_imported": int,
                "positions_failed": int,
                "csv_validation": {...}
            }

        Raises:
            InvalidAccountTypeError: account_type not in allowed list
            PortfolioExistsError: User already has portfolio with this account_name
            CSVValidationError: CSV validation failed
            Various validation errors for portfolio fields
        """
        # 1. Validate account_type
        account_type_normalized = account_type.lower().strip()
        if account_type_normalized not in ALLOWED_ACCOUNT_TYPES:
            logger.warning(f"Invalid account type: {account_type}")
            raise InvalidAccountTypeError(account_type)

        # 2. Validate account_name and check for duplicates
        account_name_normalized = account_name.strip()
        if not account_name_normalized:
            raise CSVValidationError(
                code=ERR_PORT_002,
                message="Account name is required."
            )

        # Validate account_name max length (database column is String(100))
        MAX_ACCOUNT_NAME_LENGTH = 100
        if len(account_name_normalized) > MAX_ACCOUNT_NAME_LENGTH:
            raise CSVValidationError(
                code=ERR_PORT_010,
                message=f"Account name exceeds maximum length of {MAX_ACCOUNT_NAME_LENGTH} characters.",
                details={"max_length": MAX_ACCOUNT_NAME_LENGTH, "actual_length": len(account_name_normalized)}
            )

        # Check if user already has a portfolio with this account_name
        result = await db.execute(
            select(Portfolio).where(
                Portfolio.user_id == user_id,
                Portfolio.account_name == account_name_normalized
            )
        )
        existing_portfolio = result.scalar_one_or_none()

        if existing_portfolio:
            logger.warning(f"User {user_id} already has portfolio with account_name '{account_name_normalized}'")
            raise PortfolioExistsError(str(user_id), account_name_normalized)

        # 3. Validate portfolio name
        portfolio_name_normalized = portfolio_name.strip()
        if not portfolio_name_normalized:
            raise CSVValidationError(
                code=ERR_PORT_002,
                message=get_error_message(ERR_PORT_002)
            )

        if len(portfolio_name_normalized) > MAX_PORTFOLIO_NAME_LENGTH:
            raise CSVValidationError(
                code=ERR_PORT_003,
                message=get_error_message(ERR_PORT_003),
                details={"max_length": MAX_PORTFOLIO_NAME_LENGTH}
            )

        # 3. Validate equity balance
        if not equity_balance:
            raise CSVValidationError(
                code=ERR_PORT_004,
                message=get_error_message(ERR_PORT_004)
            )

        if equity_balance <= 0:
            raise CSVValidationError(
                code=ERR_PORT_005,
                message=get_error_message(ERR_PORT_005)
            )

        if equity_balance > MAX_EQUITY_BALANCE:
            raise CSVValidationError(
                code=ERR_PORT_006,
                message=get_error_message(ERR_PORT_006),
                details={"max_balance": str(MAX_EQUITY_BALANCE)}
            )

        # 4. Validate CSV file
        if not csv_file:
            raise CSVValidationError(
                code=ERR_PORT_007,
                message=get_error_message(ERR_PORT_007)
            )

        # 5. Parse and validate CSV
        logger.info(f"Validating CSV file: {csv_file.filename}")
        csv_result = await csv_parser_service.validate_csv(csv_file)

        if not csv_result.is_valid:
            logger.warning(f"CSV validation failed with {len(csv_result.errors)} errors")
            raise CSVValidationError(
                code=ERR_PORT_008,
                message=get_error_message(ERR_PORT_008),
                details=format_csv_validation_errors(csv_result.errors)
            )

        # 6. Generate portfolio UUID (using account_name for uniqueness)
        portfolio_uuid = generate_portfolio_uuid(user_id, account_name_normalized)

        # 7. Create Portfolio
        portfolio = Portfolio(
            id=portfolio_uuid,
            user_id=user_id,
            name=portfolio_name_normalized,
            account_name=account_name_normalized,
            account_type=account_type_normalized,
            description=description.strip() if description else None,
            currency="USD",
            equity_balance=equity_balance
        )

        try:
            db.add(portfolio)
            await db.flush()  # Check for constraint violations

        except IntegrityError as e:
            # Race condition: another request created portfolio with same account_name
            logger.error(f"Portfolio creation failed due to constraint: {str(e)}")
            raise PortfolioExistsError(str(user_id), account_name_normalized)

        logger.info(f"Portfolio created: {portfolio_name_normalized} (id={portfolio.id})")

        # 8. Import positions
        import_result = await position_import_service.import_positions(
            db=db,
            portfolio_id=portfolio.id,
            user_id=user_id,
            positions_data=csv_result.positions
        )

        logger.info(
            f"Positions imported: {import_result.success_count} succeeded, "
            f"{import_result.failure_count} failed"
        )

        # 9. Return result (preprocessing will be done in calculate endpoint)
        return {
            "portfolio_id": str(portfolio.id),
            "portfolio_name": portfolio.name,
            "account_name": portfolio.account_name,
            "account_type": portfolio.account_type,
            "equity_balance": float(portfolio.equity_balance),
            "positions_imported": import_result.success_count,
            "positions_failed": import_result.failure_count,
            "total_positions": csv_result.total_rows,
            "csv_validation": {
                "valid_rows": csv_result.valid_rows,
                "total_rows": csv_result.total_rows,
                "errors": csv_result.errors
            },
            "import_errors": import_result.errors,
            "message": (
                "Portfolio created successfully. "
                "Use the /calculate endpoint to run risk analytics."
            ),
            "next_step": {
                "action": "calculate",
                "endpoint": f"/api/v1/portfolio/{portfolio.id}/calculate",
                "description": "Trigger batch calculations to populate risk metrics"
            }
        }


# Convenience instance
onboarding_service = OnboardingService()
