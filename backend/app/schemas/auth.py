"""
Authentication schemas for SigmaSight Backend
"""
from pydantic import BaseModel, EmailStr
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