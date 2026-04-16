"""
AI OS — Memory API Routes
Persistent user context management.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from models.memory import MemoryCreate, MemoryUpdate, MemoryResponse
from core.memory_manager import memory_manager
from middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/api/memory", tags=["Memory"])


@router.get("")
async def list_memories(
    user: Dict = Depends(get_current_user),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_importance: float = Query(0.0, description="Minimum importance score"),
    limit: int = Query(20, le=100, description="Max results"),
):
    """
    💾 List your persistent memories.
    Memories persist across all conversations and are auto-injected as context.

    Categories: general, preference, project, style, fact, instruction
    """
    memories = await memory_manager.retrieve(
        user_id=user["id"],
        category=category,
        min_importance=min_importance,
        limit=limit,
    )
    return {"memories": memories, "count": len(memories)}


@router.post("")
async def create_memory(
    memory: MemoryCreate,
    user: Dict = Depends(get_current_user),
):
    """
    💾 Store a new persistent memory.

    Examples:
    - {"key": "coding_language", "value": "Python", "category": "preference", "importance": 0.8}
    - {"key": "project_name", "value": "AI OS", "category": "project", "importance": 0.9}
    """
    result = await memory_manager.store(
        user_id=user["id"],
        key=memory.key,
        value=memory.value,
        category=memory.category,
        importance=memory.importance,
    )
    return {"status": "stored", "memory": result}


@router.put("/{memory_key}")
async def update_memory(
    memory_key: str,
    memory: MemoryUpdate,
    user: Dict = Depends(get_current_user),
):
    """Update an existing memory by key."""
    update_data = {}
    if memory.value is not None:
        update_data["value"] = memory.value
    if memory.category is not None:
        update_data["category"] = memory.category
    if memory.importance is not None:
        update_data["importance"] = memory.importance

    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    result = await memory_manager.store(
        user_id=user["id"],
        key=memory_key,
        value=update_data.get("value", ""),
        category=update_data.get("category", "general"),
        importance=update_data.get("importance", 0.5),
    )
    return {"status": "updated", "memory": result}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    user: Dict = Depends(get_current_user),
):
    """Delete a specific memory."""
    deleted = await memory_manager.delete(user["id"], memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted", "id": memory_id}


@router.get("/context")
async def get_memory_context(
    user: Dict = Depends(get_current_user),
):
    """
    Preview the memory context that gets injected into your AI conversations.
    """
    context = await memory_manager.get_context_prompt(user["id"])
    return {"context": context or "No memories stored yet."}
