"""
AI OS — Rate Limiter Middleware
Redis-backed rate limiting by user tier.
"""

from typing import Dict, Any
from fastapi import Request, HTTPException

from config import TIER_LIMITS
from services.redis_client import cache
from services.supabase_client import db


async def check_rate_limit(user_id: str, user_tier: str) -> Dict[str, Any]:
    """
    Check if a user has exceeded their rate limit.

    Applies two windows:
    1. Per-minute limit (RPM) — prevents burst abuse
    2. Per-day limit — enforces tier quotas

    Returns rate limit info. Raises HTTPException if exceeded.
    """
    tier_config = TIER_LIMITS.get(user_tier, TIER_LIMITS["free"])

    # ── Per-Minute Rate Limit ───────────────────────────────────
    rpm_limit = tier_config["rpm"]
    rpm_result = await cache.check_rate_limit(
        user_id=f"rpm:{user_id}",
        window_seconds=60,
        max_requests=rpm_limit,
    )

    if not rpm_result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"You've exceeded {rpm_limit} requests per minute on the {user_tier} tier.",
                "retry_after_seconds": rpm_result["reset_in"],
                "upgrade_hint": "Upgrade to Pro for 60 req/min" if user_tier == "free" else None,
            },
        )

    # ── Per-Day Rate Limit ──────────────────────────────────────
    daily_limit = tier_config["daily_requests"]
    if daily_limit > 0:  # -1 = unlimited
        daily_usage = await db.get_daily_usage(user_id)
        requests_today = daily_usage.get("request_count", 0)

        if requests_today >= daily_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Daily limit reached",
                    "message": f"You've used all {daily_limit} requests for today on the {user_tier} tier.",
                    "requests_used": requests_today,
                    "daily_limit": daily_limit,
                    "upgrade_hint": "Upgrade to Pro for unlimited requests",
                },
            )

        return {
            "allowed": True,
            "rpm_remaining": rpm_result["remaining"],
            "daily_remaining": daily_limit - requests_today,
            "daily_limit": daily_limit,
        }

    return {
        "allowed": True,
        "rpm_remaining": rpm_result["remaining"],
        "daily_remaining": -1,  # unlimited
        "daily_limit": -1,
    }
