"""
AI OS — Workflow Models
Defines multi-step AI task automation pipelines.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class WorkflowStep(BaseModel):
    """A single step in a workflow pipeline."""
    action: str  # research, write, image, summarize, translate, code, custom
    prompt: str  # Supports {{step_N_output}} template variables
    model: Optional[str] = None  # None = auto-route
    max_tokens: Optional[int] = None


class WorkflowCreate(BaseModel):
    """Create a new workflow."""
    name: str
    steps: List[WorkflowStep]
    variables: Dict[str, str] = {}  # User-defined variables like {{topic}}


class WorkflowResponse(BaseModel):
    """Workflow status and results."""
    id: str
    name: str
    status: str  # pending, running, completed, failed
    steps_total: int
    steps_completed: int = 0
    current_step: Optional[int] = None
    results: List[Dict[str, Any]] = []
    total_cost: float = 0.0
    total_tokens: int = 0
    created_at: str
    updated_at: str


class WorkflowInDB(BaseModel):
    """Workflow record as stored in database."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    steps: List[Dict[str, Any]]
    status: str = "pending"
    results: List[Dict[str, Any]] = []
    total_cost: float = 0.0
    total_tokens: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
