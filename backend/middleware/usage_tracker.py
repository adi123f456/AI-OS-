"""
AI OS — Usage Tracking Middleware
Logs every API call for analytics and billing.
"""

from typing import Dict, Any
from core.cost_tracker import cost_tracker


async def track_usage(
    user_id: str,
    endpoint: str,
    model: str = "",
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost: float = 0.0,
) -> Dict[str, Any]:
    """
    Log an API usage event.
    Called after each successful AI model call.
    """
    return await cost_tracker.log_usage(
        user_id=user_id,
        endpoint=endpoint,
        model=model,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost=cost,
    )
