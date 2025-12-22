"""
Admin Authentication utilities for SigmaSight Backend

Separate authentication system for admin users with:
- Distinct JWT claims (type: "admin")
- Shorter token expiry (8 hours vs 24 hours for regular users)
- Session tracking for token invalidation
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("admin_auth")

# Password hashing (same as regular auth)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Admin-specific constants
ADMIN_TOKEN_EXPIRY_HOURS = 8  # Shorter than user tokens (24 hours)
ADMIN_TOKEN_TYPE = "admin"


def verify_admin_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password for admin users."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Admin password verification error: {e}")
        return False


def get_admin_password_hash(password: str) -> str:
    """Hash a password for admin users."""
    return pwd_context.hash(password)


def hash_token(token: str) -> str:
    """Create a hash of a token for session storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_admin_access_token(
    admin_id: str,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token specifically for admin users.

    Args:
        admin_id: Admin user UUID as string
        email: Admin email
        role: Admin role (admin | super_admin)
        expires_delta: Optional custom expiry (defaults to 8 hours)

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ADMIN_TOKEN_EXPIRY_HOURS)

    to_encode = {
        "sub": admin_id,
        "email": email,
        "role": role,
        "type": ADMIN_TOKEN_TYPE,  # Distinguishes admin tokens from user tokens
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.info(f"Admin JWT token created for: {email} (role: {role})")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Admin JWT token creation error: {e}")
        raise


def verify_admin_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode an admin JWT token.

    Validates:
    - Token signature and expiry
    - Token type is "admin"
    - Required claims present

    Returns:
        Decoded payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Verify this is an admin token
        token_type = payload.get("type")
        if token_type != ADMIN_TOKEN_TYPE:
            logger.warning(f"Token is not admin type: {token_type}")
            return None

        # Verify required claims
        admin_id = payload.get("sub")
        if admin_id is None:
            logger.warning("Admin JWT token missing 'sub' claim")
            return None

        email = payload.get("email")
        if email is None:
            logger.warning("Admin JWT token missing 'email' claim")
            return None

        role = payload.get("role")
        if role is None:
            logger.warning("Admin JWT token missing 'role' claim")
            return None

        return payload

    except JWTError as e:
        logger.warning(f"Admin JWT token verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Admin JWT token verification error: {e}")
        return None


async def create_admin_token_response(
    admin_id: UUID,
    email: str,
    role: str,
    full_name: str
) -> Dict[str, Any]:
    """
    Create a token response for an admin user.

    Args:
        admin_id: Admin user UUID
        email: Admin email
        role: Admin role
        full_name: Admin full name

    Returns:
        Dict with access_token and metadata
    """
    access_token = create_admin_access_token(
        admin_id=str(admin_id),
        email=email,
        role=role
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ADMIN_TOKEN_EXPIRY_HOURS * 3600,  # seconds
        "admin_id": str(admin_id),
        "email": email,
        "role": role,
        "full_name": full_name
    }
