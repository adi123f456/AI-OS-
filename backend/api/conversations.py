"""
AI OS — Conversations API Routes
List conversations and fetch message history.
"""

from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query

from middleware.auth_middleware import get_current_user
from services.supabase_client import db

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.get("")
async def list_conversations(
    user: Dict = Depends(get_current_user),
    limit: int = Query(50, le=200),
):
    """List the authenticated user's conversations, newest first."""
    conversations = await db.select(
        "conversations",
        {"user_id": user["id"]},
        limit=limit,
        order_by="created_at",
        ascending=False,
    )
    return {"conversations": conversations, "count": len(conversations)}


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user: Dict = Depends(get_current_user),
    limit: int = Query(100, le=500),
):
    """Fetch all messages for a specific conversation."""
    # Verify ownership
    conv = await db.select_one("conversations", {"id": conversation_id, "user_id": user["id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await db.select(
        "messages",
        {"conversation_id": conversation_id},
        limit=limit,
        order_by="created_at",
        ascending=True,
    )
    return {
        "conversation_id": conversation_id,
        "title": conv.get("title", "Untitled"),
        "messages": messages,
        "count": len(messages),
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: Dict = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    conv = await db.select_one("conversations", {"id": conversation_id, "user_id": user["id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete("messages", {"conversation_id": conversation_id})
    await db.delete("conversations", {"id": conversation_id})
    return {"status": "deleted", "id": conversation_id}
