"""
AI OS — Conversation & Message Models
Tracks chat sessions and individual messages with model/cost metadata.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class ChatMessage(BaseModel):
    """Single message in a chat request."""
    role: str = "user"  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    """Incoming chat request from the API."""
    messages: List[ChatMessage]
    conversation_id: Optional[str] = None
    model: Optional[str] = None  # None = auto-route
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    include_memory: bool = True
    fact_check: bool = False


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    model_used: str
    content: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    confidence: Optional[float] = None
    sources: Optional[List[Dict[str, Any]]] = None
    routing_reason: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ConversationResponse(BaseModel):
    """Conversation metadata."""
    id: str
    user_id: str
    title: Optional[str] = None
    model_used: Optional[str] = None
    message_count: int = 0
    created_at: str


class MessageInDB(BaseModel):
    """Message record as stored in database."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str
    content: str
    model: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0
    metadata: Dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
