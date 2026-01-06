"""
Clerk Webhook Handler for SigmaSight.

Handles Clerk webhook events for user lifecycle and billing:
- user.created: Create user in database
- user.deleted: Soft-delete user
- subscription.created: Upgrade tier to 'paid'
- subscription.cancelled: Downgrade tier to 'free'

Uses IntegrityError for idempotency (no svix-id tracking).
Uses official svix library for signature verification with timestamp validation.

PRD Reference: Sections 10.3, 10.4
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Header, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from app.config import settings
from app.core.logging import get_logger
from app.database import get_async_session
from app.models.users import User

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_clerk_webhook(
    payload: bytes,
    headers: Dict[str, str]
) -> bool:
    """
    Verify Clerk webhook signature using official svix library.

    Uses svix library for proper signature verification with:
    - HMAC-SHA256 signature validation
    - Timestamp tolerance check (prevents replay attacks)
    - Proper handling of Clerk's webhook secret format

    Args:
        payload: Raw request body bytes
        headers: Dict with svix-id, svix-timestamp, svix-signature headers

    Returns:
        bool: True if signature is valid and timestamp is fresh

    PRD Reference: Section 10.3
    """
    if not settings.CLERK_WEBHOOK_SECRET:
        logger.error("CLERK_WEBHOOK_SECRET not configured")
        return False

    try:
        # Create svix Webhook instance with the secret
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)

        # Verify the webhook - this checks signature AND timestamp freshness
        # Raises WebhookVerificationError if invalid
        wh.verify(payload, headers)

        return True

    except WebhookVerificationError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


async def handle_user_created(data: Dict[str, Any]) -> None:
    """
    Handle user.created webhook event.

    Creates user in database if not exists (JIT may have created them first).
    Uses IntegrityError for idempotency.

    PRD Reference: Section 10.4
    """
    clerk_user_id = data.get("id")
    email = None

    # Extract email from data structure
    email_addresses = data.get("email_addresses", [])
    if email_addresses:
        primary = next(
            (e for e in email_addresses if e.get("id") == data.get("primary_email_address_id")),
            email_addresses[0]
        )
        email = primary.get("email_address")

    if not clerk_user_id or not email:
        logger.error(f"user.created webhook missing required fields: {data}")
        return

    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() or email.split("@")[0]

    async with get_async_session() as db:
        try:
            new_user = User(
                id=uuid4(),
                email=email,
                clerk_user_id=clerk_user_id,
                full_name=full_name,
                hashed_password="clerk_managed",  # Clerk handles auth
                tier="free",
                invite_validated=False,
                ai_messages_used=0,
                ai_messages_reset_at=datetime.now(timezone.utc),
                is_active=True,
            )
            db.add(new_user)
            await db.commit()
            logger.info(f"Created user from webhook: {email} (clerk_id: {clerk_user_id})")

        except IntegrityError:
            # User already exists (JIT provisioning or duplicate webhook)
            await db.rollback()
            logger.info(f"User already exists (idempotent): {email}")


async def handle_user_deleted(data: Dict[str, Any]) -> None:
    """
    Handle user.deleted webhook event.

    Soft-deletes user by setting is_active=False.
    Does not delete data for audit purposes.

    PRD Reference: Section 10.4
    """
    clerk_user_id = data.get("id")

    if not clerk_user_id:
        logger.error("user.deleted webhook missing clerk user ID")
        return

    async with get_async_session() as db:
        stmt = select(User).where(User.clerk_user_id == clerk_user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            await db.commit()
            logger.info(f"Soft-deleted user: {user.email} (clerk_id: {clerk_user_id})")
        else:
            logger.warning(f"user.deleted: User not found for clerk_id: {clerk_user_id}")


async def handle_subscription_created(data: Dict[str, Any]) -> None:
    """
    Handle subscription.created webhook event.

    Upgrades user tier to 'paid' when they subscribe.

    PRD Reference: Section 10.4
    """
    # Clerk Billing uses 'user_id' in subscription events
    clerk_user_id = data.get("user_id")
    plan_key = data.get("plan", {}).get("key", "")

    if not clerk_user_id:
        logger.error("subscription.created webhook missing user_id")
        return

    # Map Clerk plan keys to our tier system
    # free_user -> "free", pro_user -> "paid"
    new_tier = "paid" if plan_key == "pro_user" else "free"

    async with get_async_session() as db:
        stmt = select(User).where(User.clerk_user_id == clerk_user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            old_tier = user.tier
            user.tier = new_tier
            await db.commit()
            logger.info(
                f"User {user.email} tier changed: {old_tier} -> {new_tier} "
                f"(plan: {plan_key})"
            )
        else:
            logger.warning(
                f"subscription.created: User not found for clerk_id: {clerk_user_id}"
            )


async def handle_subscription_cancelled(data: Dict[str, Any]) -> None:
    """
    Handle subscription.cancelled webhook event.

    Downgrades user tier to 'free' when subscription ends.

    PRD Reference: Section 10.4
    """
    clerk_user_id = data.get("user_id")

    if not clerk_user_id:
        logger.error("subscription.cancelled webhook missing user_id")
        return

    async with get_async_session() as db:
        stmt = select(User).where(User.clerk_user_id == clerk_user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            old_tier = user.tier
            user.tier = "free"
            await db.commit()
            logger.info(
                f"User {user.email} subscription cancelled: {old_tier} -> free"
            )
        else:
            logger.warning(
                f"subscription.cancelled: User not found for clerk_id: {clerk_user_id}"
            )


@router.post("/clerk")
async def handle_clerk_webhook(
    request: Request,
    svix_id: Optional[str] = Header(None, alias="svix-id"),
    svix_timestamp: Optional[str] = Header(None, alias="svix-timestamp"),
    svix_signature: Optional[str] = Header(None, alias="svix-signature"),
):
    """
    Clerk webhook endpoint.

    Receives and processes Clerk webhook events for:
    - User lifecycle (created, deleted)
    - Billing events (subscription created/cancelled)

    Uses official svix library for signature verification with timestamp validation.

    PRD Reference: Section 10.3
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature (skip in development if no secret configured)
    if settings.CLERK_WEBHOOK_SECRET:
        if not svix_id or not svix_timestamp or not svix_signature:
            logger.warning("Webhook received without required svix headers")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature headers"
            )

        # Build headers dict for svix verification
        svix_headers = {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        }

        if not verify_clerk_webhook(body, svix_headers):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    else:
        logger.warning("CLERK_WEBHOOK_SECRET not set, skipping signature verification")

    # Parse the webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    event_type = payload.get("type")
    event_data = payload.get("data", {})

    logger.info(f"Received Clerk webhook: {event_type} (svix-id: {svix_id})")

    # Route to appropriate handler
    handlers = {
        "user.created": handle_user_created,
        "user.deleted": handle_user_deleted,
        "subscription.created": handle_subscription_created,
        "subscription.cancelled": handle_subscription_cancelled,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(event_data)
    else:
        logger.debug(f"Unhandled webhook event type: {event_type}")

    # Always return 200 to acknowledge receipt
    return {"status": "received", "type": event_type}
