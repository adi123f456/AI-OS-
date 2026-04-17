"""
AI OS — Auth API Routes
User registration, login, token management, and profile.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
import uuid

from models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from utils.security import hash_password, verify_password, create_access_token, generate_api_key, decode_access_token
from services.supabase_client import db
from utils.helpers import validate_email
from middleware.auth_middleware import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ── Pydantic models for request bodies ─────────────────────────────

class TokenRefreshRequest(BaseModel):
    """Request body for token refresh."""
    token: str


# ── Register ──────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """
    Register a new user account.
    Returns a JWT access token on success.
    """
    # Validate email
    if not validate_email(user_data.email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Check password strength
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check if user already exists
    existing = await db.select_one("users", {"email": user_data.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user_id = str(uuid.uuid4())
    api_key = generate_api_key()

    user_record = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "tier": "free",
        "api_key": api_key,
    }

    await db.insert("users", user_record)

    # Generate JWT
    token = create_access_token(
        user_id=user_id,
        email=user_data.email,
        tier="free",
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            tier="free",
        ),
    )


# ── Login ─────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """
    Login with email and password.
    Returns a JWT access token.
    """
    # Find user
    user = await db.select_one("users", {"email": user_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(user_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT
    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        tier=user.get("tier", "free"),
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            tier=user.get("tier", "free"),
        ),
    )


# ── Refresh Token ─────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: TokenRefreshRequest):
    """
    Refresh an existing token.
    Send the current token in the body to get a fresh one.
    """
    try:
        payload = decode_access_token(body.token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await db.select_one("users", {"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        tier=user.get("tier", "free"),
    )

    return TokenResponse(
        access_token=new_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            tier=user.get("tier", "free"),
        ),
    )


# ── Get Profile (/me) ─────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_profile(user: Dict = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    Requires a valid Bearer token.
    """
    return UserResponse(
        id=user["id"],
        email=user["email"],
        tier=user.get("tier", "free"),
        created_at=user.get("created_at"),
    )
