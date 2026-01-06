"""
FastAPI dependencies for authentication and authorization

Includes:
- Legacy auth (get_current_user) - Uses internal JWT
- Clerk auth (get_current_user_clerk) - Uses Clerk JWT + JWKS
- Validated user guard (get_validated_user) - Requires invite validation
"""
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Optional, Annotated

from app.core.auth import verify_token
from app.database import get_db
from app.models.users import User, Portfolio
from app.schemas.auth import CurrentUser
from app.core.logging import auth_logger

# HTTP Bearer token security scheme (with auto_error=False for dual auth)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_cookie: Optional[str] = Cookie(None, alias="auth_token"),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """
    Dependency to get the current authenticated user.
    Supports dual authentication: Bearer token (preferred) or Cookie (fallback).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try Bearer token first (preferred for regular API calls)
    token = None
    auth_method = None
    
    if credentials and credentials.credentials:
        token = credentials.credentials
        auth_method = "bearer"
        auth_logger.debug("Using Bearer token authentication")
    # Fall back to cookie (needed for SSE)
    elif auth_cookie:
        token = auth_cookie
        auth_method = "cookie"
        auth_logger.debug("Using cookie authentication")
    else:
        auth_logger.warning("No valid authentication provided (neither Bearer nor cookie)")
        raise credentials_exception
    
    try:
        # Verify and decode the JWT token (same logic regardless of source)
        payload = verify_token(token)
        if payload is None:
            auth_logger.warning(f"Token verification failed (auth method: {auth_method})")
            raise credentials_exception
        
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            auth_logger.warning(f"No subject in token (auth method: {auth_method})")
            raise credentials_exception
        
        # Convert string to UUID
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            auth_logger.warning(f"Invalid UUID format in token: {user_id_str} (auth method: {auth_method})")
            raise credentials_exception
        
    except HTTPException:
        raise
    except Exception as e:
        auth_logger.error(f"Token validation error: {e} (auth method: {auth_method})")
        raise credentials_exception
    
    # Get user from database
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            auth_logger.warning(f"User not found in database: {user_id}")
            raise credentials_exception
        
        if not user.is_active:
            auth_logger.warning(f"Inactive user attempted access: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        # Log successful authentication with method used
        auth_logger.info(f"User authenticated successfully: {user.email} (method: {auth_method})")
        
        # Query user portfolios and set default_portfolio_id for guaranteed fallback
        # Implements PORTFOLIO_ID_DESIGN_DOC Section 8.1.5: /api/v1/me must always return portfolio_id
        portfolio_stmt = select(Portfolio).where(Portfolio.user_id == user.id)
        portfolio_result = await db.execute(portfolio_stmt)
        portfolios = portfolio_result.scalars().all()
        default_portfolio_id = portfolios[0].id if portfolios else None
        
        # Create CurrentUser with guaranteed portfolio_id for consistent auth context
        user_data = CurrentUser.model_validate(user)
        user_data.portfolio_id = default_portfolio_id
        
        if default_portfolio_id:
            auth_logger.debug(f"Portfolio context resolved for user {user.email}: {default_portfolio_id}")
        else:
            auth_logger.warning(f"No portfolio found for user {user.email}")
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        auth_logger.error(f"Database error during user lookup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Dependency to get the current active user (redundant check but explicit)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


# Optional user dependency (doesn't raise if no token)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    auth_cookie: Optional[str] = Cookie(None, alias="auth_token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[CurrentUser]:
    """
    Optional dependency that returns None if no valid token is provided.
    Supports both Bearer token and cookie authentication.
    """
    if not credentials and not auth_cookie:
        return None
    
    try:
        # Reuse the existing dual-auth logic but catch exceptions
        return await get_current_user(credentials, auth_cookie, db)
    except HTTPException:
        return None
    except Exception:
        return None


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Dependency that requires admin privileges.
    For now, just requires authenticated user - can be enhanced later.
    """
    # TODO: Add proper admin role check
    # For demo stage, any authenticated user can access admin endpoints
    return current_user


async def validate_portfolio_ownership(
    db: AsyncSession,
    portfolio_id: UUID,
    user_id: UUID
) -> None:
    """
    Validate that a portfolio belongs to the specified user.
    
    Args:
        db: Database session
        portfolio_id: Portfolio UUID to validate
        user_id: User UUID who should own the portfolio
        
    Raises:
        ValueError: If portfolio not found or not owned by user
    """
    portfolio_stmt = select(Portfolio).where(
        and_(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id
        )
    )
    portfolio_result = await db.execute(portfolio_stmt)
    portfolio = portfolio_result.scalar_one_or_none()
    
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found or not owned by user {user_id}")


async def resolve_portfolio_id(
    portfolio_id: Optional[UUID],
    current_user: CurrentUser,
    db: AsyncSession
) -> UUID:
    """
    Helper function for Backend Implicit Default Resolution (PORTFOLIO_ID_DESIGN_DOC Section 8.1.6)
    
    Server resolves default portfolio using user ID when portfolio_id is missing.
    Leverages single-portfolio constraint to reduce client fragility.
    
    Args:
        portfolio_id: Optional portfolio_id from request
        current_user: Authenticated user from dependency
        db: Database session
        
    Returns:
        UUID: Resolved portfolio_id (either provided or default for user)
        
    Raises:
        HTTPException: If user has no portfolios
    """
    if portfolio_id:
        # Portfolio ID provided, verify ownership and return
        portfolio_stmt = select(Portfolio).where(
            and_(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            )
        )
        portfolio_result = await db.execute(portfolio_stmt)
        portfolio = portfolio_result.scalar_one_or_none()
        
        if not portfolio:
            auth_logger.warning(f"Portfolio {portfolio_id} not found or not owned by user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found or access denied"
            )
        
        return portfolio_id
    
    # Portfolio ID not provided, resolve default using user ID
    portfolio_stmt = select(Portfolio).where(Portfolio.user_id == current_user.id)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolios = portfolio_result.scalars().all()
    
    if not portfolios:
        auth_logger.warning(f"No portfolios found for user {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No portfolios found for user"
        )
    
    default_portfolio_id = portfolios[0].id
    auth_logger.debug(f"Resolved default portfolio for user {current_user.email}: {default_portfolio_id}")

    return default_portfolio_id


# =============================================================================
# Clerk Authentication Dependencies (Phase 2)
# =============================================================================

# Import Clerk auth module (lazy import to avoid circular dependencies)
def _get_clerk_auth():
    from app.core.clerk_auth import get_current_user_clerk
    return get_current_user_clerk


async def get_validated_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    clerk_session: Optional[str] = Cookie(None, alias="__session"),
) -> User:
    """
    Combined dependency: Clerk auth + invite validation.

    Use this for protected endpoints that require:
    1. Valid Clerk JWT authentication
    2. Validated invite code

    PRD Reference: Section 9.5

    Args:
        db: Database session
        credentials: Bearer token from Authorization header
        clerk_session: JWT from Clerk's __session cookie (SSE fallback)

    Returns:
        User with validated invite

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If invite not validated
    """
    # Get Clerk auth dependency
    get_current_user_clerk = _get_clerk_auth()

    # Authenticate with Clerk
    user = await get_current_user_clerk(
        credentials=credentials,
        clerk_session=clerk_session,
        db=db
    )

    # Check invite validation
    if not user.invite_validated:
        auth_logger.warning(f"User {user.email} attempted access without invite validation")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "invite_required",
                "message": "Please enter your invite code in Settings to access this feature",
                "redirect": "/settings"
            }
        )

    return user


# Type alias for validated user dependency (PRD Section 9.5)
ValidatedUser = Annotated[User, Depends(get_validated_user)]


async def get_current_user_clerk_optional(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    clerk_session: Optional[str] = Cookie(None, alias="__session"),
) -> Optional[User]:
    """
    Optional Clerk authentication dependency.

    Returns None if no valid token provided (doesn't raise).
    Useful for endpoints that have different behavior for authenticated vs anonymous users.
    """
    if not credentials and not clerk_session:
        return None

    try:
        get_current_user_clerk = _get_clerk_auth()
        return await get_current_user_clerk(
            credentials=credentials,
            clerk_session=clerk_session,
            db=db
        )
    except HTTPException:
        return None
    except Exception:
        return None
