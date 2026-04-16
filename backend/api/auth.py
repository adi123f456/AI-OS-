"""
AI OS — Auth API Routes
User registration, login, and token management.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import uuid

from models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from utils.security import hash_password, verify_password, create_access_token, generate_api_key
from services.supabase_client import db
from utils.helpers import validate_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


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


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_token: Dict[str, str]):
    """
    Refresh an existing token.
    Send the current token to get a new one.
    """
    from utils.security import decode_access_token

    try:
        payload = decode_access_token(current_token.get("token", ""))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

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


@router.get("/me", response_model=UserResponse)
async def get_profile(user: Dict = None):
    """Get current user profile."""
    from middleware.auth_middleware import get_current_user
    from fastapi import Depends, Request

    # This will be used with Depends(get_current_user) in main
    if user:
        return UserResponse(
            id=user["id"],
            email=user["email"],
            tier=user.get("tier", "free"),
            created_at=user.get("created_at"),
        )
    raise HTTPException(status_code=401, detail="Not authenticated")
