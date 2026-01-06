"""
Authentication schemas for SigmaSight Backend
"""
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class CurrentUser(BaseModel):
    """Schema for the current authenticated user with guaranteed portfolio_id"""
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    portfolio_id: Optional[UUID] = None  # Added portfolio_id for guaranteed fallback

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login request"""
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """Schema for user registration request"""
    email: EmailStr
    password: str
    full_name: str


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data"""
    user_id: Optional[UUID] = None
    email: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema for token response with user info"""
    access_token: str
    token_type: str = "bearer"
    user: CurrentUser


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserMeResponse(BaseModel):
    """
    Enhanced /me response with entitlements for Clerk auth.

    Includes user info, subscription tier, and usage limits.
    PRD Reference: Section 15.1.1

    Example response:
    {
        "id": "uuid...",
        "email": "user@example.com",
        "full_name": "John Doe",
        "is_active": true,
        "tier": "free",
        "invite_validated": true,
        "portfolio_count": 1,
        "limits": {
            "max_portfolios": 2,
            "max_ai_messages": 100,
            "ai_messages_used": 15,
            "ai_messages_remaining": 85
        }
    }
    """
    # Core user info
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime

    # Clerk auth fields
    tier: str = Field(default="free", description="Subscription tier: 'free' or 'paid'")
    invite_validated: bool = Field(default=False, description="Whether invite code has been validated")

    # Portfolio info
    portfolio_id: Optional[UUID] = Field(default=None, description="Default portfolio ID")
    portfolio_count: int = Field(default=0, description="Number of portfolios owned")

    # Usage limits
    limits: dict = Field(
        default_factory=lambda: {
            "max_portfolios": 2,
            "max_ai_messages": 100,
            "ai_messages_used": 0,
            "ai_messages_remaining": 100,
        },
        description="Tier-based usage limits and current usage"
    )

    class Config:
        from_attributes = True