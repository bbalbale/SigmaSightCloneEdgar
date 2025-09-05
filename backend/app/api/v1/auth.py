"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from app.database import get_db
from app.core.auth import verify_password, get_password_hash, create_token_response
from app.core.dependencies import get_current_user
from app.models.users import User, Portfolio
from app.schemas.auth import UserLogin, UserRegister, TokenResponse, UserResponse, CurrentUser
from app.core.logging import auth_logger
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login")
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT token (in response body AND cookie)"""
    auth_logger.info(f"Login attempt for email: {user_login.email}")
    
    # Get user by email
    stmt = select(User).where(User.email == user_login.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        auth_logger.warning(f"Login failed - user not found: {user_login.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        auth_logger.warning(f"Login failed - inactive user: {user_login.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account"
        )
    
    if not verify_password(user_login.password, user.hashed_password):
        auth_logger.warning(f"Login failed - incorrect password: {user_login.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Query user portfolios and set default_portfolio = portfolios[0].id
    portfolio_stmt = select(Portfolio).where(Portfolio.user_id == user.id)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolios = portfolio_result.scalars().all()
    default_portfolio_id = str(portfolios[0].id) if portfolios else None
    
    # Create JWT token with guaranteed portfolio_id in claims
    token_data = await create_token_response(str(user.id), user.email, default_portfolio_id)
    auth_logger.info(f"Login successful for user: {user.email}, portfolio: {default_portfolio_id}")
    
    # Create response with token in body (for existing clients)
    response = JSONResponse(content={
        "access_token": token_data["access_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"]
    })
    
    # ALSO set token as HTTP-only cookie (for SSE support)
    # Convert expires_in (seconds) to max_age for cookie
    max_age = token_data.get("expires_in", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    response.set_cookie(
        key="auth_token",
        value=token_data["access_token"],
        httponly=True,
        samesite="lax" if settings.ENVIRONMENT != "production" else "none",
        secure=settings.ENVIRONMENT == "production",
        max_age=max_age,
        domain=getattr(settings, "COOKIE_DOMAIN", None) if settings.ENVIRONMENT == "production" else None
    )
    
    auth_logger.info(f"Set auth cookie for user: {user.email} (expires in {max_age}s)")
    
    return response


@router.post("/register", response_model=UserResponse)
async def register(user_register: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user (admin-only initially)"""
    auth_logger.info(f"Registration attempt for email: {user_register.email}")
    
    # Check if user already exists
    stmt = select(User).where(User.email == user_register.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        auth_logger.warning(f"Registration failed - email already exists: {user_register.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_register.password)
    new_user = User(
        id=uuid4(),
        email=user_register.email,
        full_name=user_register.full_name,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db.add(new_user)
    
    # Create portfolio for the user
    portfolio = Portfolio(
        id=uuid4(),
        user_id=new_user.id,
        name=f"{user_register.full_name}'s Portfolio"
    )
    
    db.add(portfolio)
    
    try:
        await db.commit()
        await db.refresh(new_user)
        auth_logger.info(f"User registered successfully: {user_register.email}")
        return UserResponse.model_validate(new_user)
    except Exception as e:
        await db.rollback()
        auth_logger.error(f"Registration failed for {user_register.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.get("/me", response_model=CurrentUser)
async def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """Get current authenticated user information"""
    auth_logger.info(f"User info requested: {current_user.email}")
    return current_user


@router.post("/refresh")
async def refresh_token(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Refresh JWT token (returns new token in body AND cookie)"""
    auth_logger.info(f"Token refresh requested: {current_user.email}")
    
    # Query user portfolios for consistent portfolio_id in refreshed token
    portfolio_stmt = select(Portfolio).where(Portfolio.user_id == current_user.id)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolios = portfolio_result.scalars().all()
    default_portfolio_id = str(portfolios[0].id) if portfolios else None
    
    # Create a new token with guaranteed portfolio_id in claims
    token_data = await create_token_response(str(current_user.id), current_user.email, default_portfolio_id)
    
    # Create response with token in body (for existing clients)
    response = JSONResponse(content={
        "access_token": token_data["access_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"]
    })
    
    # ALSO set token as HTTP-only cookie (for SSE support)
    max_age = token_data.get("expires_in", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    response.set_cookie(
        key="auth_token",
        value=token_data["access_token"],
        httponly=True,
        samesite="lax" if settings.ENVIRONMENT != "production" else "none",
        secure=settings.ENVIRONMENT == "production",
        max_age=max_age,
        domain=getattr(settings, "COOKIE_DOMAIN", None) if settings.ENVIRONMENT == "production" else None
    )
    
    auth_logger.info(f"Refreshed auth token for user: {current_user.email} (expires in {max_age}s)")
    
    return response


@router.post("/logout")
async def logout(
    response: Response,
    current_user: CurrentUser = Depends(get_current_user)
):
    """Logout endpoint - clears auth cookie and instructs client to discard token"""
    auth_logger.info(f"Logout requested: {current_user.email}")
    
    # Clear the auth cookie
    response.delete_cookie(
        key="auth_token",
        samesite="lax" if settings.ENVIRONMENT != "production" else "none",
        secure=settings.ENVIRONMENT == "production",
        domain=getattr(settings, "COOKIE_DOMAIN", None) if settings.ENVIRONMENT == "production" else None
    )
    
    auth_logger.info(f"Cleared auth cookie for user: {current_user.email}")
    
    # Note: Client should also discard any stored Bearer tokens
    # In a future version, we could implement token blacklisting
    return {"message": "Successfully logged out", "success": True}
