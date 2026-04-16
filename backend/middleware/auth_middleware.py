"""
AI OS — Auth Middleware
JWT verification and user extraction for protected routes.
"""

from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from utils.security import decode_access_token
from services.supabase_client import db

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Extract and verify the current user from JWT token.
    Use as a FastAPI dependency on protected routes.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Look up user in DB
    user = await db.select_one("users", {"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Attach user to request state
    request.state.user = user
    request.state.user_tier = user.get("tier", "free")

    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """
    Extract user if token is provided, otherwise return None.
    For endpoints that work both authenticated and anonymously.
    """
    if not credentials:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id:
            user = await db.select_one("users", {"id": user_id})
            if user:
                request.state.user = user
                request.state.user_tier = user.get("tier", "free")
                return user
    except:
        pass

    return None
