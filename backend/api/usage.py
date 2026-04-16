"""
AI OS — Usage API Route
Track limits, costs, and usage per tier.
"""

from typing import Dict
from fastapi import APIRouter, Depends

from models.usage import UsageSummary
from core.cost_tracker import cost_tracker
from core.model_router import router as model_router
from middleware.auth_middleware import get_current_user
from config import TIER_LIMITS

router = APIRouter(prefix="/api/usage", tags=["Usage"])


@router.get("", response_model=UsageSummary)
async def get_usage(
    user: Dict = Depends(get_current_user),
):
    """
    📊 Get your current usage statistics.

    Returns:
    - Requests used today vs daily limit
    - Tokens consumed today
    - Cost breakdown (today + this month)
    - Rate limit info (RPM)
    - Available models for your tier
    """
    user_id = user["id"]
    user_tier = user.get("tier", "free")
    tier_config = TIER_LIMITS.get(user_tier, TIER_LIMITS["free"])

    # Get today's usage
    today = await cost_tracker.get_user_usage_today(user_id)
    requests_today = today.get("request_count", 0)
    tokens_today = today.get("total_tokens", 0)
    cost_today = float(today.get("total_cost", 0))

    # Get monthly usage
    month = await cost_tracker.get_user_usage_month(user_id)
    cost_month = month.get("total_cost", 0.0)

    # Calculate remaining
    daily_limit = tier_config["daily_requests"]
    if daily_limit > 0:
        remaining = max(0, daily_limit - requests_today)
    else:
        remaining = -1  # unlimited

    # Get available models
    models = model_router.get_available_models(user_tier)
    model_names = [m["name"] for m in models]

    return UsageSummary(
        tier=user_tier,
        requests_today=requests_today,
        daily_limit=daily_limit if daily_limit > 0 else -1,
        requests_remaining=remaining,
        tokens_today=tokens_today,
        cost_today=round(cost_today, 6),
        cost_this_month=round(cost_month, 6),
        rpm_limit=tier_config["rpm"],
        models_available=model_names,
    )


@router.get("/breakdown")
async def get_cost_breakdown(
    user: Dict = Depends(get_current_user),
):
    """Get cost breakdown by model."""
    breakdown = await cost_tracker.get_cost_breakdown(user["id"])
    return {
        "tier": user.get("tier", "free"),
        "breakdown": breakdown,
    }
