"""
Admin Authentication API endpoints

Provides:
- POST /admin/auth/login - Admin login (email/password)
- POST /admin/auth/logout - Admin logout (invalidates session)
- GET /admin/auth/me - Get current admin info
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.admin import AdminUser, AdminSession
from app.core.admin_auth import (
    verify_admin_password,
    create_admin_access_token,
    create_admin_token_response,
    hash_token,
    ADMIN_TOKEN_EXPIRY_HOURS
)
from app.core.admin_dependencies import CurrentAdmin, get_current_admin
from app.core.logging import get_logger

logger = get_logger("admin_auth_api")

router = APIRouter(prefix="/admin/auth", tags=["Admin - Authentication"])


# ========== Schemas ==========

class AdminLoginRequest(BaseModel):
    """Admin login request schema."""
    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    """Admin login response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_id: str
    email: str
    role: str
    full_name: str


class AdminMeResponse(BaseModel):
    """Admin me response schema."""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# ========== Endpoints ==========

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    request: Request,
    login_data: AdminLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate admin user and return JWT token.

    - Validates email/password against admin_users table
    - Creates session record for tracking/invalidation
    - Returns JWT with type: "admin" claim
    - Sets optional cookie for browser auth
    """
    # Find admin by email
    stmt = select(AdminUser).where(AdminUser.email == login_data.email)
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        logger.warning(f"Admin login failed - email not found: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_admin_password(login_data.password, admin.hashed_password):
        logger.warning(f"Admin login failed - invalid password for: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if admin is active
    if not admin.is_active:
        logger.warning(f"Admin login failed - inactive account: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is inactive"
        )

    # Create token response
    token_response = await create_admin_token_response(
        admin_id=admin.id,
        email=admin.email,
        role=admin.role,
        full_name=admin.full_name
    )

    # Create session record for tracking
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    expires_at = datetime.utcnow() + timedelta(hours=ADMIN_TOKEN_EXPIRY_HOURS)

    session = AdminSession(
        admin_user_id=admin.id,
        token_hash=hash_token(token_response["access_token"]),
        ip_address=client_ip,
        user_agent=user_agent[:500] if user_agent else None,  # Truncate long user agents
        expires_at=expires_at
    )
    db.add(session)

    # Update last login
    admin.last_login_at = datetime.utcnow()

    await db.commit()

    logger.info(f"Admin login successful: {admin.email} from IP: {client_ip}")

    # Set cookie for browser auth (optional, alongside bearer token)
    response.set_cookie(
        key="admin_auth_token",
        value=token_response["access_token"],
        httponly=True,
        secure=True,  # Requires HTTPS in production
        samesite="lax",
        max_age=ADMIN_TOKEN_EXPIRY_HOURS * 3600
    )

    return AdminLoginResponse(**token_response)


@router.post("/logout", response_model=MessageResponse)
async def admin_logout(
    request: Request,
    response: Response,
    current_admin: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout admin user and invalidate session.

    - Removes session record from database
    - Clears auth cookie
    """
    # Get token from authorization header or cookie
    auth_header = request.headers.get("authorization")
    token = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.cookies.get("admin_auth_token")

    if token:
        # Delete the session record
        token_hash_value = hash_token(token)
        stmt = select(AdminSession).where(
            AdminSession.admin_user_id == current_admin.id,
            AdminSession.token_hash == token_hash_value
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            await db.delete(session)
            await db.commit()

    logger.info(f"Admin logout: {current_admin.email}")

    # Clear the auth cookie
    response.delete_cookie(key="admin_auth_token")

    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=AdminMeResponse)
async def admin_me(
    current_admin: CurrentAdmin = Depends(get_current_admin)
):
    """
    Get current admin user information.

    Returns admin profile data without sensitive information.
    """
    return AdminMeResponse(
        id=str(current_admin.id),
        email=current_admin.email,
        full_name=current_admin.full_name,
        role=current_admin.role,
        is_active=current_admin.is_active,
        created_at=current_admin.created_at,
        last_login_at=current_admin.last_login_at
    )


@router.post("/refresh", response_model=AdminLoginResponse)
async def admin_refresh_token(
    request: Request,
    response: Response,
    current_admin: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh admin access token.

    - Validates current token
    - Creates new token with fresh expiry
    - Updates session record
    - Returns new token
    """
    # Get old token
    auth_header = request.headers.get("authorization")
    old_token = None

    if auth_header and auth_header.startswith("Bearer "):
        old_token = auth_header[7:]
    else:
        old_token = request.cookies.get("admin_auth_token")

    # Get admin user from database (to ensure fresh data)
    stmt = select(AdminUser).where(AdminUser.id == current_admin.id)
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is invalid or inactive"
        )

    # Create new token
    token_response = await create_admin_token_response(
        admin_id=admin.id,
        email=admin.email,
        role=admin.role,
        full_name=admin.full_name
    )

    # Update session record
    if old_token:
        old_token_hash = hash_token(old_token)
        stmt = select(AdminSession).where(
            AdminSession.admin_user_id == admin.id,
            AdminSession.token_hash == old_token_hash
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.token_hash = hash_token(token_response["access_token"])
            session.expires_at = datetime.utcnow() + timedelta(hours=ADMIN_TOKEN_EXPIRY_HOURS)
        else:
            # Create new session if old one not found
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

            new_session = AdminSession(
                admin_user_id=admin.id,
                token_hash=hash_token(token_response["access_token"]),
                ip_address=client_ip,
                user_agent=user_agent[:500] if user_agent else None,
                expires_at=datetime.utcnow() + timedelta(hours=ADMIN_TOKEN_EXPIRY_HOURS)
            )
            db.add(new_session)

    await db.commit()

    logger.info(f"Admin token refreshed: {admin.email}")

    # Set new cookie
    response.set_cookie(
        key="admin_auth_token",
        value=token_response["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ADMIN_TOKEN_EXPIRY_HOURS * 3600
    )

    return AdminLoginResponse(**token_response)
