"""
AI OS — Waitlist API Route
Server-side email capture (replaces client-side Supabase call).
"""

from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase_client import db
from utils.helpers import validate_email

router = APIRouter(prefix="/api/waitlist", tags=["Waitlist"])


class WaitlistRequest(BaseModel):
    email: str


class WaitlistResponse(BaseModel):
    status: str
    message: str


@router.post("", response_model=WaitlistResponse)
async def join_waitlist(request: WaitlistRequest):
    """
    📧 Join the AI OS waitlist.
    No authentication required.
    """
    email = request.email.strip().lower()

    # Validate email
    if not validate_email(email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Check if already registered
    existing = await db.select_one("waitlist", {"email": email})
    if existing:
        return WaitlistResponse(
            status="exists",
            message="You're already on the waitlist!",
        )

    # Add to waitlist
    await db.insert("waitlist", {"email": email})

    return WaitlistResponse(
        status="success",
        message="You're on the list! We'll notify you when AI OS launches.",
    )


@router.get("/count")
async def get_waitlist_count():
    """Get total waitlist count (public endpoint)."""
    entries = await db.select("waitlist", limit=10000)
    return {"count": len(entries)}
