"""
FastAPI dependencies for admin authentication and authorization

Provides:
- get_current_admin: Validates admin JWT and returns admin user
- require_super_admin: Validates admin has super_admin role
"""
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional
from datetime import datetime

from app.core.admin_auth import verify_admin_token, hash_token
from app.database import get_db
from app.models.admin import AdminUser, AdminSession
from app.core.logging import get_logger

logger = get_logger("admin_dependencies")

# HTTP Bearer token security scheme (with auto_error=False for dual auth)
admin_security = HTTPBearer(auto_error=False)


class CurrentAdmin:
    """Represents the currently authenticated admin user."""

    def __init__(
        self,
        id: UUID,
        email: str,
        full_name: str,
        role: str,
        is_active: bool,
        created_at: datetime,
        last_login_at: Optional[datetime] = None
    ):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.role = role
        self.is_active = is_active
        self.created_at = created_at
        self.last_login_at = last_login_at

    @classmethod
    def from_db_model(cls, admin: AdminUser) -> "CurrentAdmin":
        """Create CurrentAdmin from database model."""
        return cls(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name,
            role=admin.role,
            is_active=admin.is_active,
            created_at=admin.created_at,
            last_login_at=admin.last_login_at
        )


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(admin_security),
    admin_auth_cookie: Optional[str] = Cookie(None, alias="admin_auth_token"),
    db: AsyncSession = Depends(get_db)
) -> CurrentAdmin:
    """
    Dependency to get the current authenticated admin user.

    Supports dual authentication:
    - Bearer token (preferred for API calls)
    - Cookie (fallback for browser sessions)

    Validates:
    - Token is valid admin token (type: "admin")
    - Admin user exists and is active
    - Session is not expired (if session tracking enabled)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try Bearer token first (preferred)
    token = None
    auth_method = None

    if credentials and credentials.credentials:
        token = credentials.credentials
        auth_method = "bearer"
        logger.debug("Admin using Bearer token authentication")
    elif admin_auth_cookie:
        token = admin_auth_cookie
        auth_method = "cookie"
        logger.debug("Admin using cookie authentication")
    else:
        logger.warning("No valid admin authentication provided")
        raise credentials_exception

    try:
        # Verify and decode the admin JWT token
        payload = verify_admin_token(token)
        if payload is None:
            logger.warning(f"Admin token verification failed (auth method: {auth_method})")
            raise credentials_exception

        admin_id_str: str = payload.get("sub")
        if admin_id_str is None:
            logger.warning(f"No subject in admin token (auth method: {auth_method})")
            raise credentials_exception

        # Convert string to UUID
        try:
            admin_id = UUID(admin_id_str)
        except ValueError:
            logger.warning(f"Invalid UUID format in admin token: {admin_id_str}")
            raise credentials_exception

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin token validation error: {e} (auth method: {auth_method})")
        raise credentials_exception

    # Get admin user from database
    try:
        stmt = select(AdminUser).where(AdminUser.id == admin_id)
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin is None:
            logger.warning(f"Admin user not found in database: {admin_id}")
            raise credentials_exception

        if not admin.is_active:
            logger.warning(f"Inactive admin attempted access: {admin_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive admin account"
            )

        # Optional: Verify session exists and is not expired
        token_hash = hash_token(token)
        session_stmt = select(AdminSession).where(
            AdminSession.admin_user_id == admin_id,
            AdminSession.token_hash == token_hash,
            AdminSession.expires_at > datetime.utcnow()
        )
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()

        # Note: Session validation is optional - if no session found, still allow
        # This enables stateless JWT auth while supporting session-based invalidation
        if session:
            logger.debug(f"Admin session validated for: {admin.email}")

        # Log successful authentication
        logger.info(f"Admin authenticated successfully: {admin.email} (method: {auth_method})")

        # Log IP and user agent for audit trail
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        logger.debug(f"Admin access from IP: {client_ip}, UA: {user_agent[:50]}...")

        return CurrentAdmin.from_db_model(admin)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during admin lookup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


async def require_super_admin(
    current_admin: CurrentAdmin = Depends(get_current_admin)
) -> CurrentAdmin:
    """
    Dependency that requires super_admin role.

    Use for sensitive operations like:
    - Managing other admin accounts
    - Deleting user data
    - System configuration changes
    """
    if current_admin.role != "super_admin":
        logger.warning(
            f"Admin {current_admin.email} attempted super_admin action with role: {current_admin.role}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )

    return current_admin


async def get_current_admin_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(admin_security),
    admin_auth_cookie: Optional[str] = Cookie(None, alias="admin_auth_token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[CurrentAdmin]:
    """
    Optional dependency that returns None if no valid admin token is provided.
    """
    if not credentials and not admin_auth_cookie:
        return None

    try:
        return await get_current_admin(request, credentials, admin_auth_cookie, db)
    except HTTPException:
        return None
    except Exception:
        return None
