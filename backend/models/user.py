"""
AI OS — User Model
Defines user accounts, tiers, and API keys.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
import uuid


# ── Pydantic Schemas (API layer) ───────────────────────────────────

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: str
    password: str


class UserLogin(BaseModel):
    """Schema for user login."""
    email: str
    password: str


class UserResponse(BaseModel):
    """Schema for user data returned in API responses."""
    id: str
    email: str
    tier: str = "free"
    created_at: Optional[str] = None


class UserInDB(BaseModel):
    """Full user record as stored in database."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    tier: str = "free"
    api_key: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
