"""
Onboarding API Endpoints

Provides user registration and portfolio creation endpoints for beta onboarding.

Endpoints:
- POST /api/v1/onboarding/register - User registration with invite code
- POST /api/v1/onboarding/create-portfolio - Portfolio creation with CSV import
- GET /api/v1/onboarding/csv-template - Download CSV template

All endpoints follow the error handling framework with structured error codes.
"""
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, UploadFile, File, Form, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.users import User
from app.services.onboarding_service import onboarding_service
from app.core.logging import get_logger
from app.services.activity_tracking_service import (
    track_register_start,
    track_register_complete,
    track_register_error,
    track_portfolio_start,
    track_portfolio_complete,
    track_portfolio_error,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ==============================================================================
# Request/Response Schemas
# ==============================================================================

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=255)
    invite_code: str


class RegisterResponse(BaseModel):
    """User registration response"""
    user_id: str
    email: str
    full_name: str
    message: str
    next_step: dict


class CreatePortfolioResponse(BaseModel):
    """Portfolio creation response"""
    portfolio_id: str
    portfolio_name: str
    account_name: str
    account_type: str
    equity_balance: float
    positions_imported: int
    positions_failed: int
    total_positions: int
    message: str
    next_step: dict


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_user(
    request_body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with invite code.

    Requires a valid beta invite code. Creates user account with:
    - Email validation (unique, valid format)
    - Password strength validation (8+ chars, upper/lower/digit)
    - Full name validation

    Returns user details and next steps.

    **Errors:**
    - 401: Invalid invite code (ERR_INVITE_001)
    - 409: Email already exists (ERR_USER_001)
    - 422: Invalid email format (ERR_USER_002)
    - 422: Weak password (ERR_USER_003)
    - 422: Invalid full name (ERR_USER_004)
    """
    logger.info(f"Registration attempt: {request_body.email}")

    # Extract client info for tracking
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Track registration start
    track_register_start(
        email=request_body.email,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    try:
        # Register user (service validates everything)
        user = await onboarding_service.register_user(
            email=request_body.email,
            password=request_body.password,
            full_name=request_body.full_name,
            invite_code=request_body.invite_code,
            db=db
        )

        # Commit transaction
        await db.commit()

        logger.info(f"User registered successfully: {user.email}")

        # Track successful registration
        track_register_complete(
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return RegisterResponse(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            message="Account created successfully! You can now log in and create your portfolio.",
            next_step={
                "action": "login",
                "endpoint": "/api/v1/auth/login",
                "description": "Log in with your email and password to get access token"
            }
        )
    except Exception as e:
        # Track registration error
        error_code = getattr(e, 'detail', {}).get('code', 'UNKNOWN_ERROR') if hasattr(e, 'detail') and isinstance(e.detail, dict) else str(type(e).__name__)
        error_message = str(e.detail) if hasattr(e, 'detail') else str(e)
        track_register_error(
            error_code=error_code,
            error_message=error_message,
            email=request_body.email,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise


@router.post("/create-portfolio", response_model=CreatePortfolioResponse, status_code=201)
async def create_portfolio(
    request: Request,
    portfolio_name: str = Form(..., description="Portfolio display name"),
    account_name: str = Form(..., description="Portfolio account name (unique per user)"),
    account_type: str = Form(..., description="Account type (taxable, ira, roth_ira, 401k, 403b, 529, hsa, trust, other)"),
    equity_balance: Decimal = Form(..., description="Total account equity balance"),
    description: Optional[str] = Form(None, description="Optional portfolio description"),
    csv_file: UploadFile = File(..., description="CSV file with positions"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create portfolio with CSV import.

    Requires authentication. Creates portfolio with:
    - Portfolio name (display name) and account name (unique identifier)
    - Account type (taxable, ira, roth_ira, 401k, 403b, 529, hsa, trust, other)
    - Equity balance (total account value)
    - Positions imported from CSV file

    CSV must match the template format (12 columns).
    Download template at: GET /api/v1/onboarding/csv-template

    **Fast response (<5s)** - No preprocessing or calculations.
    Use POST /api/v1/portfolio/{id}/calculate to run analytics.

    **Errors:**
    - 400: Invalid account type (ERR_PORT_009)
    - 400: CSV validation failed (ERR_CSV_*, ERR_POS_*)
    - 409: User already has portfolio with this account_name (ERR_PORT_001)
    - 422: Invalid portfolio fields (ERR_PORT_002-007)

    **Constraints:**
    - Account name must be unique per user
    - Multiple portfolios allowed per user (Phase 2)
    - Checked at application level AND database level (unique constraint)
    """
    logger.info(f"Portfolio creation attempt for user {current_user.id} (account_name='{account_name}')")

    # Extract client info for tracking
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Track portfolio creation start
    track_portfolio_start(
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    try:
        # Create portfolio with CSV import
        result = await onboarding_service.create_portfolio_with_csv(
            user_id=current_user.id,
            portfolio_name=portfolio_name,
            account_name=account_name,
            account_type=account_type,
            equity_balance=equity_balance,
            csv_file=csv_file,
            description=description,
            db=db
        )

        # Commit transaction
        await db.commit()

        logger.info(
            f"Portfolio created successfully: {result['portfolio_id']} "
            f"with {result['positions_imported']} positions"
        )

        # Track successful portfolio creation
        from uuid import UUID
        track_portfolio_complete(
            user_id=current_user.id,
            portfolio_id=UUID(result['portfolio_id']),
            portfolio_name=result['portfolio_name'],
            position_count=result['positions_imported'],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return CreatePortfolioResponse(**result)

    except Exception as e:
        # Track portfolio creation error
        error_code = getattr(e, 'detail', {}).get('code', 'UNKNOWN_ERROR') if hasattr(e, 'detail') and isinstance(e.detail, dict) else str(type(e).__name__)
        error_message = str(e.detail) if hasattr(e, 'detail') else str(e)
        track_portfolio_error(
            user_id=current_user.id,
            error_code=error_code,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise


@router.get("/csv-template", response_class=PlainTextResponse)
async def download_csv_template():
    """
    Download CSV template for portfolio import.

    Returns a 12-column CSV template with:
    - Header row with column names
    - Instruction comments (lines starting with #)
    - Example positions (stocks, options, ETFs)

    **Columns:**
    1. Symbol (required)
    2. Quantity (required, can be negative for shorts)
    3. Entry Price Per Share (required)
    4. Entry Date (required, YYYY-MM-DD)
    5. Investment Class (optional: PUBLIC, OPTIONS, PRIVATE)
    6. Investment Subtype (optional)
    7. Underlying Symbol (for options)
    8. Strike Price (for options)
    9. Expiration Date (for options, YYYY-MM-DD)
    10. Option Type (for options: CALL or PUT)
    11. Exit Date (optional, YYYY-MM-DD)
    12. Exit Price Per Share (optional)

    **Cache:** 1 hour
    """
    logger.info("CSV template download requested")

    template_content = '''# SigmaSight Portfolio Import Template
# ==========================================
# Instructions:
# 1. Fill in your positions below the header row
# 2. Required columns: Symbol, Quantity, Entry Price Per Share, Entry Date
# 3. For options: Use a descriptive symbol (e.g., SPY_C450_20240315) + fill options columns
# 4. For closed positions: Fill in Exit Date and Exit Price Per Share
# 5. Negative quantity = short position
# 6. Date format: YYYY-MM-DD
# 7. Comment lines (starting with #) are automatically ignored - no need to remove them
#
# Account Types (used when creating portfolio):
# - taxable: Standard brokerage account
# - ira: Traditional IRA
# - roth_ira: Roth IRA
# - 401k: 401(k) retirement plan
# - 403b: 403(b) retirement plan
# - 529: 529 education savings plan
# - hsa: Health Savings Account
# - trust: Trust account
# - other: Other account types
#
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
# Example: Stock position (long)
AAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,
# Example: Long call option
SPY_C450_20240315,10,5.50,2024-02-01,OPTIONS,,SPY,450.00,2024-03-15,CALL,,
# Example: Long put option
AAPL_P160_20240315,5,3.25,2024-02-05,OPTIONS,,AAPL,160.00,2024-03-15,PUT,,
# Example: ETF position
QQQ,50,445.20,2024-01-20,PUBLIC,ETF,,,,,,
# Example: Short stock position (negative quantity)
SHOP,-25,62.50,2024-02-10,PUBLIC,STOCK,,,,,,
# Example: Cash/Money Market
SPAXX,10000,1.00,2024-01-01,PUBLIC,CASH,,,,,,
# Example: Closed position (with exit date/price)
TSLA,50,185.00,2023-12-01,PUBLIC,STOCK,,,,2024-01-15,215.00
'''

    return Response(
        content=template_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=sigmasight_portfolio_template.csv",
            "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
        }
    )
