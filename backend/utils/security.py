"""
AI OS — Security Utilities
Password hashing, JWT tokens, API key generation, encryption.
"""

import hashlib
import hmac
import secrets
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import bcrypt
import jwt

from config import settings


# ── Password Hashing ────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


# ── JWT Tokens ──────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    email: str,
    tier: str = "free",
    expires_minutes: int = None,
) -> str:
    """Create a JWT access token."""
    if expires_minutes is None:
        expires_minutes = settings.jwt_expiry_minutes

    payload = {
        "sub": user_id,
        "email": email,
        "tier": tier,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.
    Raises jwt.InvalidTokenError if invalid or expired.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )


# ── API Key Generation ──────────────────────────────────────────────

def generate_api_key(prefix: str = "aios") -> str:
    """Generate a secure API key."""
    random_part = secrets.token_hex(24)
    return f"{prefix}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage (we only store hashes)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


# ── Data Encryption Helpers ─────────────────────────────────────────

def generate_encryption_key() -> str:
    """Generate a random encryption key."""
    return secrets.token_hex(32)


def mask_sensitive(value: str, show_last: int = 4) -> str:
    """Mask a sensitive value, showing only the last N characters."""
    if len(value) <= show_last:
        return "*" * len(value)
    return "*" * (len(value) - show_last) + value[-show_last:]
