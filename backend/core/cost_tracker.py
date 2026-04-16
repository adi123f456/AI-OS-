"""
AI OS — Cost Tracker
Tracks and reports costs per model call, per user, per day.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
import uuid

from services.supabase_client import db


class CostTracker:
    """
    Tracks AI model usage costs at a granular level.
    Logs every API call with token counts and calculated costs.
    """

    async def log_usage(
        self,
        user_id: str,
        endpoint: str,
        model: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Log a single API usage event.
        """
        log_entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "endpoint": endpoint,
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost": cost,
            "created_at": datetime.utcnow().isoformat(),
        }

        await db.insert("usage_logs", log_entry)

        # Also increment daily aggregate
        await db.increment_daily_usage(
            user_id=user_id,
            tokens=tokens_input + tokens_output,
            cost=cost,
        )

        return log_entry

    async def get_user_usage_today(self, user_id: str) -> Dict[str, Any]:
        """Get a user's usage for today."""
        return await db.get_daily_usage(user_id)

    async def get_user_usage_month(self, user_id: str) -> Dict[str, Any]:
        """Get a user's total usage for the current month."""
        # Get all daily usage records for this month
        today = date.today()
        month_start = today.replace(day=1).isoformat()

        # Query all usage logs for the month
        logs = await db.select(
            "usage_logs",
            {"user_id": user_id},
            limit=5000,
        )

        # Filter for current month
        month_logs = [
            l for l in logs
            if l.get("created_at", "") >= month_start
        ]

        total_cost = sum(float(l.get("cost", 0)) for l in month_logs)
        total_tokens = sum(
            int(l.get("tokens_input", 0)) + int(l.get("tokens_output", 0))
            for l in month_logs
        )
        total_requests = len(month_logs)

        return {
            "month": today.strftime("%Y-%m"),
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
        }

    async def get_cost_breakdown(self, user_id: str) -> List[Dict[str, Any]]:
        """Get cost breakdown by model for a user."""
        logs = await db.select(
            "usage_logs",
            {"user_id": user_id},
            limit=5000,
        )

        # Aggregate by model
        breakdown: Dict[str, Dict] = {}
        for log in logs:
            model = log.get("model", "unknown")
            if model not in breakdown:
                breakdown[model] = {
                    "model": model,
                    "calls": 0,
                    "tokens": 0,
                    "cost": 0.0,
                }
            breakdown[model]["calls"] += 1
            breakdown[model]["tokens"] += int(log.get("tokens_input", 0)) + int(log.get("tokens_output", 0))
            breakdown[model]["cost"] += float(log.get("cost", 0))

        # Sort by cost descending
        result = sorted(breakdown.values(), key=lambda x: x["cost"], reverse=True)
        for item in result:
            item["cost"] = round(item["cost"], 6)

        return result


# Singleton
cost_tracker = CostTracker()
