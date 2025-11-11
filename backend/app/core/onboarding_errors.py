"""
Onboarding Error Handling Framework

Provides structured error codes and exception classes for user onboarding.
All errors include:
- Structured error codes (ERR_*)
- User-friendly messages
- HTTP status codes
- Optional details for debugging

Error Categories:
- ERR_INVITE_*: Invite code validation errors
- ERR_USER_*: User registration errors
- ERR_CSV_*: CSV file validation errors
- ERR_POS_*: Position validation errors
- ERR_PORT_*: Portfolio creation errors
- ERR_BATCH_*: Batch processing prerequisite errors
- ERR_ADMIN_*: Admin/superuser errors
"""
from typing import Any, Optional, Dict, List
from fastapi import HTTPException


# ==============================================================================
# Base Exception Classes
# ==============================================================================

class OnboardingException(Exception):
    """Base exception for all onboarding errors"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: Any = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


# ==============================================================================
# Specific Exception Classes
# ==============================================================================

class InviteCodeError(OnboardingException):
    """Invalid or missing invite code"""

    def __init__(self, details: Any = None):
        super().__init__(
            code="ERR_INVITE_001",
            message="Invalid invite code. Please check your invite code and try again.",
            status_code=401,
            details=details,
        )


class UserExistsError(OnboardingException):
    """User with email already exists"""

    def __init__(self, email: str, details: Any = None):
        super().__init__(
            code="ERR_USER_001",
            message=f"An account with email '{email}' already exists.",
            status_code=409,
            details=details or {"email": email},
        )


class InvalidEmailError(OnboardingException):
    """Invalid email format"""

    def __init__(self, email: str, details: Any = None):
        super().__init__(
            code="ERR_USER_002",
            message=f"Invalid email format: '{email}'",
            status_code=422,
            details=details or {"email": email},
        )


class WeakPasswordError(OnboardingException):
    """Password does not meet strength requirements"""

    def __init__(self, details: Any = None):
        super().__init__(
            code="ERR_USER_003",
            message="Password must be at least 8 characters and contain uppercase, lowercase, and numbers.",
            status_code=422,
            details=details,
        )


class InvalidFullNameError(OnboardingException):
    """Full name is empty or invalid"""

    def __init__(self, details: Any = None):
        super().__init__(
            code="ERR_USER_004",
            message="Full name is required and cannot be empty.",
            status_code=422,
            details=details,
        )


class CSVValidationError(OnboardingException):
    """CSV file validation failed"""

    def __init__(self, code: str, message: str, details: Any = None):
        super().__init__(
            code=code,
            message=message,
            status_code=400,
            details=details,
        )


class PortfolioExistsError(OnboardingException):
    """User already has a portfolio with this account name"""

    def __init__(self, user_id: str, account_name: str, details: Any = None):
        super().__init__(
            code="ERR_PORT_001",
            message="You already have a portfolio with this account name. Please use a different account name.",
            status_code=409,
            details=details or {"user_id": user_id, "account_name": account_name},
        )


class InvalidAccountTypeError(OnboardingException):
    """Invalid account type provided"""

    def __init__(self, account_type: str, details: Any = None):
        super().__init__(
            code="ERR_PORT_009",
            message="Invalid account type. Must be one of: taxable, ira, roth_ira, 401k, 403b, 529, hsa, trust, other.",
            status_code=400,
            details=details or {"account_type": account_type},
        )


class BatchPrerequisiteError(OnboardingException):
    """Portfolio not ready for batch processing"""

    def __init__(self, message: str, details: Any = None):
        super().__init__(
            code="ERR_BATCH_001",
            message=message,
            status_code=409,
            details=details,
        )


class NotSuperuserError(OnboardingException):
    """User is not a superuser"""

    def __init__(self, details: Any = None):
        super().__init__(
            code="ERR_ADMIN_001",
            message="This action requires superuser privileges.",
            status_code=403,
            details=details,
        )


class TargetUserNotFoundError(OnboardingException):
    """Target user for impersonation not found"""

    def __init__(self, user_id: str, details: Any = None):
        super().__init__(
            code="ERR_ADMIN_002",
            message=f"User with ID '{user_id}' not found.",
            status_code=404,
            details=details or {"user_id": user_id},
        )


class SelfImpersonationError(OnboardingException):
    """Cannot impersonate self"""

    def __init__(self, details: Any = None):
        super().__init__(
            code="ERR_ADMIN_003",
            message="You cannot impersonate yourself.",
            status_code=400,
            details=details,
        )


# ==============================================================================
# CSV Validation Error Factory
# ==============================================================================

def create_csv_error(
    error_code: str,
    message: str,
    row_number: Optional[int] = None,
    field: Optional[str] = None,
    value: Optional[str] = None,
) -> CSVValidationError:
    """
    Create a structured CSV validation error.

    Args:
        error_code: Error code (ERR_CSV_* or ERR_POS_*)
        message: User-friendly error message
        row_number: Row number where error occurred (optional)
        field: Field name where error occurred (optional)
        value: Invalid value (optional)

    Returns:
        CSVValidationError with structured details
    """
    details: Dict[str, Any] = {}

    if row_number is not None:
        details["row"] = row_number
    if field:
        details["field"] = field
    if value:
        details["value"] = value

    return CSVValidationError(
        code=error_code,
        message=message,
        details=details if details else None,
    )


# ==============================================================================
# Error Response Helpers
# ==============================================================================

def create_error_response(
    code: str,
    message: str,
    details: Any = None,
    documentation_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.

    Args:
        code: Error code
        message: User-friendly message
        details: Optional additional details
        documentation_url: Optional link to error documentation

    Returns:
        Standardized error response dictionary
    """
    response = {
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details is not None:
        response["error"]["details"] = details

    if documentation_url:
        response["error"]["documentation_url"] = documentation_url
    else:
        # Generate documentation URL from error code
        response["error"]["documentation_url"] = f"https://docs.sigmasight.io/errors/{code}"

    return response


def format_csv_validation_errors(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format multiple CSV validation errors into a single response.

    Args:
        errors: List of error dictionaries with row/field/message info

    Returns:
        Formatted error response with all validation errors
    """
    return {
        "error": {
            "code": "ERR_CSV_VALIDATION",
            "message": f"CSV validation failed with {len(errors)} error(s)",
            "details": {
                "errors": errors,
                "total_errors": len(errors),
            },
            "documentation_url": "https://docs.sigmasight.io/errors/ERR_CSV_VALIDATION"
        }
    }


# ==============================================================================
# CSV Error Code Constants
# ==============================================================================

# File-level errors
ERR_CSV_001 = "ERR_CSV_001"  # File too large
ERR_CSV_002 = "ERR_CSV_002"  # Invalid file type
ERR_CSV_003 = "ERR_CSV_003"  # Empty file
ERR_CSV_004 = "ERR_CSV_004"  # Missing required column
ERR_CSV_005 = "ERR_CSV_005"  # Invalid header format
ERR_CSV_006 = "ERR_CSV_006"  # Malformed CSV

# Position validation errors
ERR_POS_001 = "ERR_POS_001"  # Symbol required
ERR_POS_002 = "ERR_POS_002"  # Symbol too long
ERR_POS_003 = "ERR_POS_003"  # Symbol invalid characters
ERR_POS_004 = "ERR_POS_004"  # Quantity required
ERR_POS_005 = "ERR_POS_005"  # Quantity not numeric
ERR_POS_006 = "ERR_POS_006"  # Quantity zero
ERR_POS_007 = "ERR_POS_007"  # Quantity too many decimals
ERR_POS_008 = "ERR_POS_008"  # Entry price required
ERR_POS_009 = "ERR_POS_009"  # Entry price not numeric
ERR_POS_010 = "ERR_POS_010"  # Entry price not positive
ERR_POS_011 = "ERR_POS_011"  # Entry price too many decimals
ERR_POS_012 = "ERR_POS_012"  # Entry date required
ERR_POS_013 = "ERR_POS_013"  # Entry date invalid format
ERR_POS_014 = "ERR_POS_014"  # Entry date in future
ERR_POS_015 = "ERR_POS_015"  # Entry date too old
ERR_POS_016 = "ERR_POS_016"  # Invalid investment class
ERR_POS_017 = "ERR_POS_017"  # Invalid investment subtype
ERR_POS_018 = "ERR_POS_018"  # Exit date before entry date
ERR_POS_019 = "ERR_POS_019"  # Options: missing underlying
ERR_POS_020 = "ERR_POS_020"  # Options: missing strike
ERR_POS_021 = "ERR_POS_021"  # Options: missing expiration
ERR_POS_022 = "ERR_POS_022"  # Options: missing type (call/put)
ERR_POS_023 = "ERR_POS_023"  # Duplicate position

# Portfolio creation errors
ERR_PORT_001 = "ERR_PORT_001"  # Portfolio already exists
ERR_PORT_002 = "ERR_PORT_002"  # Portfolio name required
ERR_PORT_003 = "ERR_PORT_003"  # Portfolio name too long
ERR_PORT_004 = "ERR_PORT_004"  # Equity balance required
ERR_PORT_005 = "ERR_PORT_005"  # Equity balance not positive
ERR_PORT_006 = "ERR_PORT_006"  # Equity balance unreasonable
ERR_PORT_007 = "ERR_PORT_007"  # CSV file required
ERR_PORT_008 = "ERR_PORT_008"  # CSV validation failed
ERR_PORT_009 = "ERR_PORT_009"  # Invalid account type
ERR_PORT_010 = "ERR_PORT_010"  # Account name too long
ERR_PORT_011 = "ERR_PORT_011"  # Account name required


# ==============================================================================
# Error Messages
# ==============================================================================

CSV_ERROR_MESSAGES = {
    ERR_CSV_001: "File size exceeds maximum limit of 10MB",
    ERR_CSV_002: "Invalid file type. Only .csv files are accepted",
    ERR_CSV_003: "CSV file is empty or contains no data rows",
    ERR_CSV_004: "Missing required column: {column}",
    ERR_CSV_005: "Invalid CSV header format",
    ERR_CSV_006: "Malformed CSV file. Please check file formatting",

    ERR_POS_001: "Symbol is required",
    ERR_POS_002: "Symbol exceeds maximum length of 100 characters",
    ERR_POS_003: "Symbol contains invalid characters",
    ERR_POS_004: "Quantity is required",
    ERR_POS_005: "Quantity must be a valid number",
    ERR_POS_006: "Quantity cannot be zero",
    ERR_POS_007: "Quantity has too many decimal places (max 6)",
    ERR_POS_008: "Entry price is required",
    ERR_POS_009: "Entry price must be a valid number",
    ERR_POS_010: "Entry price must be positive",
    ERR_POS_011: "Entry price has too many decimal places (max 2)",
    ERR_POS_012: "Entry date is required",
    ERR_POS_013: "Entry date must be in YYYY-MM-DD format",
    ERR_POS_014: "Entry date cannot be in the future",
    ERR_POS_015: "Entry date cannot be more than 100 years old",
    ERR_POS_016: "Invalid investment class. Must be PUBLIC, OPTIONS, or PRIVATE",
    ERR_POS_017: "Invalid investment subtype for the specified class",
    ERR_POS_018: "Exit date cannot be before entry date",
    ERR_POS_019: "Options position missing underlying symbol",
    ERR_POS_020: "Options position missing strike price",
    ERR_POS_021: "Options position missing expiration date",
    ERR_POS_022: "Options position missing type (CALL or PUT)",
    ERR_POS_023: "Duplicate position detected (same symbol and entry date)",
}


def get_error_message(error_code: str, **kwargs) -> str:
    """
    Get formatted error message for an error code.

    Args:
        error_code: Error code (ERR_*)
        **kwargs: Format arguments for message template

    Returns:
        Formatted error message
    """
    template = CSV_ERROR_MESSAGES.get(error_code, "Unknown error")
    return template.format(**kwargs) if kwargs else template
