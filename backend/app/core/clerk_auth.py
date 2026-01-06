"""
Clerk Authentication Module for SigmaSight Backend

Provides JWT verification using Clerk's JWKS endpoint with:
- Async JWKS fetch with TTL cache
- RS256 JWT verification
- JIT (Just-In-Time) user provisioning for webhook race conditions

PRD Reference: Section 5.3
"""
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from cachetools import TTLCache
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.exceptions import JWKError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import get_db
from app.models.users import User, Portfolio
from app.core.logging import auth_logger

# HTTP Bearer token security scheme
clerk_security = HTTPBearer(auto_error=False)

# JWKS cache: 1 hour TTL, max 10 keys (Clerk rotates keys periodically)
_jwks_cache: TTLCache = TTLCache(maxsize=10, ttl=3600)


async def get_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS from Clerk's well-known endpoint with TTL caching.

    Returns:
        Dict containing JWKS keys for JWT verification

    Raises:
        HTTPException: If JWKS fetch fails
    """
    cache_key = "clerk_jwks"

    # Return cached JWKS if available
    if cache_key in _jwks_cache:
        return _jwks_cache[cache_key]

    # Fetch fresh JWKS from Clerk
    jwks_url = f"https://{settings.CLERK_DOMAIN}/.well-known/jwks.json"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks_data = response.json()

            # Cache the JWKS
            _jwks_cache[cache_key] = jwks_data
            auth_logger.info(f"JWKS fetched and cached from {jwks_url}")

            return jwks_data

    except httpx.HTTPError as e:
        auth_logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable"
        )
    except Exception as e:
        auth_logger.error(f"Unexpected error fetching JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


def get_signing_key(jwks: Dict[str, Any], token: str) -> Optional[Dict[str, Any]]:
    """
    Get the appropriate signing key from JWKS based on token's kid header.

    Args:
        jwks: JWKS data from Clerk
        token: JWT token to find key for

    Returns:
        Matching JWK or None
    """
    try:
        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            auth_logger.warning("JWT token missing 'kid' header")
            return None

        # Find matching key in JWKS
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key

        auth_logger.warning(f"No matching key found for kid: {kid}")
        return None

    except JWTError as e:
        auth_logger.warning(f"Error parsing JWT header: {e}")
        return None


async def verify_clerk_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Clerk JWT token using JWKS.

    Args:
        token: JWT token from Authorization header

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        # Get JWKS
        jwks = await get_jwks()

        # Get signing key for this token
        signing_key = get_signing_key(jwks, token)
        if not signing_key:
            return None

        # Build RSA public key from JWK
        try:
            public_key = jwk.construct(signing_key)
        except JWKError as e:
            auth_logger.error(f"Failed to construct key from JWK: {e}")
            return None

        # Verify and decode the token
        # Clerk uses RS256 algorithm
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.CLERK_AUDIENCE if settings.CLERK_AUDIENCE else None,
            options={
                "verify_aud": bool(settings.CLERK_AUDIENCE),
                "verify_exp": True,
                "verify_iat": True,
            }
        )

        return payload

    except jwt.ExpiredSignatureError:
        auth_logger.warning("Clerk JWT token has expired")
        return None
    except jwt.JWTClaimsError as e:
        auth_logger.warning(f"Clerk JWT claims error: {e}")
        return None
    except JWTError as e:
        auth_logger.warning(f"Clerk JWT verification failed: {e}")
        return None
    except Exception as e:
        auth_logger.error(f"Unexpected error verifying Clerk token: {e}")
        return None


async def get_user_by_clerk_id(db: AsyncSession, clerk_user_id: str) -> Optional[User]:
    """
    Get user by Clerk user ID.

    Args:
        db: Database session
        clerk_user_id: Clerk's user identifier (e.g., "user_2abc123...")

    Returns:
        User if found, None otherwise
    """
    stmt = select(User).where(User.clerk_user_id == clerk_user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def jit_provision_user(
    db: AsyncSession,
    clerk_user_id: str,
    email: str,
    full_name: Optional[str] = None
) -> User:
    """
    Just-In-Time user provisioning for webhook race conditions.

    If Clerk JWT arrives before webhook, create user from JWT claims.
    Uses IntegrityError for idempotency (if webhook already created user).

    PRD Reference: Section 5.3.2

    Args:
        db: Database session
        clerk_user_id: Clerk's user identifier
        email: User's email from JWT claims
        full_name: User's name from JWT claims (optional)

    Returns:
        User (either newly created or existing)
    """
    try:
        # Create new user from JWT claims
        new_user = User(
            id=uuid4(),
            email=email,
            clerk_user_id=clerk_user_id,
            full_name=full_name or email.split("@")[0],  # Fallback to email prefix
            hashed_password="clerk_managed",  # Placeholder - Clerk handles auth
            tier="free",
            invite_validated=False,
            ai_messages_used=0,
            ai_messages_reset_at=datetime.utcnow(),
            is_active=True,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        auth_logger.info(f"JIT provisioned user: {email} (clerk_id: {clerk_user_id})")
        return new_user

    except IntegrityError:
        # User already exists (webhook arrived first or concurrent request)
        await db.rollback()

        # Fetch the existing user
        existing_user = await get_user_by_clerk_id(db, clerk_user_id)
        if existing_user:
            auth_logger.info(f"JIT found existing user: {email} (clerk_id: {clerk_user_id})")
            return existing_user

        # Edge case: IntegrityError but user not found by clerk_id
        # Could be email conflict - try by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user_by_email = result.scalar_one_or_none()

        if user_by_email:
            # Link existing user to Clerk
            user_by_email.clerk_user_id = clerk_user_id
            await db.commit()
            auth_logger.info(f"Linked existing user to Clerk: {email}")
            return user_by_email

        auth_logger.error(f"JIT provisioning failed unexpectedly for: {email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User provisioning failed"
        )


async def get_current_user_clerk(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(clerk_security),
    clerk_session: Optional[str] = Cookie(None, alias="__session"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current user from Clerk JWT.

    Supports dual authentication:
    - Bearer token (preferred for API calls)
    - Clerk session cookie (fallback for SSE connections where headers can't be set)

    Clerk uses `__session` cookie for the session JWT.
    Note: `__client` cookie is NOT a JWT - it's a metadata blob and cannot be decoded.
    EventSource (SSE) cannot set custom headers, so cookie-based auth is required.

    Includes JIT provisioning for webhook race conditions.

    Args:
        credentials: Bearer token from Authorization header
        clerk_session: JWT from Clerk's __session cookie (SSE fallback)
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Get token from Bearer header or Clerk session cookie
    token = None
    auth_method = None

    if credentials and credentials.credentials:
        token = credentials.credentials
        auth_method = "bearer"
    elif clerk_session:
        # Clerk's __session cookie contains the JWT
        token = clerk_session
        auth_method = "cookie:__session"
    else:
        auth_logger.warning("No Clerk authentication provided (no Bearer header or __session cookie)")
        raise credentials_exception

    # Verify Clerk JWT
    payload = await verify_clerk_token(token)
    if payload is None:
        auth_logger.warning(f"Clerk token verification failed (method: {auth_method})")
        raise credentials_exception

    # Extract Clerk user ID from 'sub' claim
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        auth_logger.warning("Clerk JWT missing 'sub' claim")
        raise credentials_exception

    # Try to get user by Clerk ID
    user = await get_user_by_clerk_id(db, clerk_user_id)

    if user is None:
        # JIT provisioning: create user from JWT claims
        email = payload.get("email") or payload.get("email_addresses", [{}])[0].get("email_address")
        if not email:
            auth_logger.warning("Clerk JWT missing email claim")
            raise credentials_exception

        full_name = payload.get("first_name", "") + " " + payload.get("last_name", "")
        full_name = full_name.strip() or None

        user = await jit_provision_user(db, clerk_user_id, email, full_name)

    # Check if user is active
    if not user.is_active:
        auth_logger.warning(f"Inactive Clerk user attempted access: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    auth_logger.info(f"Clerk user authenticated: {user.email} (method: {auth_method})")
    return user


# Convenience function to clear JWKS cache (useful for testing)
def clear_jwks_cache():
    """Clear the JWKS cache to force a fresh fetch."""
    _jwks_cache.clear()
    auth_logger.info("JWKS cache cleared")
