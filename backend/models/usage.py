"""
AI OS — Usage Tracking Models
Tracks API calls, tokens, costs per user per day.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class UsageLog(BaseModel):
    """Individual API call log."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    endpoint: str
    model: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DailyUsage(BaseModel):
    """Aggregated daily usage for a user."""
    user_id: str
    date: str
    request_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


class UsageSummary(BaseModel):
    """Complete usage summary returned to the user."""
    tier: str
    requests_today: int = 0
    daily_limit: int = 50
    requests_remaining: int = 50
    tokens_today: int = 0
    cost_today: float = 0.0
    cost_this_month: float = 0.0
    rpm_limit: int = 5
    models_available: list = []
