"""
AI OS — Memory Models
Persistent user context that survives across conversations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import uuid


class MemoryCreate(BaseModel):
    """Create a new memory entry."""
    key: str
    value: str
    category: str = "general"  # general, preference, project, style, fact
    importance: float = 0.5  # 0.0 to 1.0


class MemoryUpdate(BaseModel):
    """Update an existing memory."""
    value: Optional[str] = None
    category: Optional[str] = None
    importance: Optional[float] = None


class MemoryResponse(BaseModel):
    """Memory returned in API responses."""
    id: str
    key: str
    value: str
    category: str
    importance: float
    created_at: str
    updated_at: str


class MemoryInDB(BaseModel):
    """Memory record as stored in database."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    key: str
    value: str
    category: str = "general"
    importance: float = 0.5
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryQuery(BaseModel):
    """Query parameters for fetching memories."""
    category: Optional[str] = None
    min_importance: float = 0.0
    limit: int = 20
