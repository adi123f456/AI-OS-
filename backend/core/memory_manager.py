"""
AI OS — Memory Manager
Persistent user memory across conversations.
Stores preferences, project context, and learned facts.
Auto-injects relevant memories into system prompts.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import re

from services.supabase_client import db


class MemoryManager:
    """
    Manages persistent user memory.
    Memories are key-value pairs with categories and importance scores.
    High-importance memories are auto-injected into AI prompts.
    """

    CATEGORIES = ["general", "preference", "project", "style", "fact", "instruction"]

    async def store(
        self,
        user_id: str,
        key: str,
        value: str,
        category: str = "general",
        importance: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Store or update a memory.

        Args:
            user_id: The user's ID
            key: Memory identifier (e.g., "preferred_language")
            value: Memory content (e.g., "Python")
            category: Category for organization
            importance: Priority score 0.0-1.0
        """
        # Check if memory with this key already exists
        existing = await db.select_one(
            "user_memory",
            {"user_id": user_id, "key": key}
        )

        if existing:
            result = await db.update(
                "user_memory",
                {"user_id": user_id, "key": key},
                {
                    "value": value,
                    "category": category,
                    "importance": importance,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            return result
        else:
            data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "key": key,
                "value": value,
                "category": category,
                "importance": importance,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            return await db.insert("user_memory", data)

    async def retrieve(
        self,
        user_id: str,
        category: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories for a user, optionally filtered by category."""
        filters = {"user_id": user_id}
        if category:
            filters["category"] = category

        memories = await db.select(
            "user_memory",
            filters,
            limit=limit,
            order_by="importance",
            ascending=False,
        )

        # Filter by importance in-memory (Supabase doesn't support > easily)
        if min_importance > 0:
            memories = [m for m in memories if m.get("importance", 0) >= min_importance]

        return memories

    async def delete(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        return await db.delete("user_memory", {"id": memory_id, "user_id": user_id})

    async def get_context_prompt(self, user_id: str) -> str:
        """
        Build a system prompt section from the user's important memories.
        This gets prepended to AI conversations for personalization.
        """
        # Get high-importance memories
        memories = await self.retrieve(
            user_id,
            min_importance=0.3,
            limit=15,
        )

        if not memories:
            return ""

        # Build context string
        lines = ["## User Context (from persistent memory):"]
        for mem in memories:
            category = mem.get("category", "general")
            key = mem.get("key", "")
            value = mem.get("value", "")
            lines.append(f"- [{category}] {key}: {value}")

        return "\n".join(lines)

    async def auto_extract_memories(
        self,
        user_id: str,
        message: str,
        response: str,
    ) -> List[Dict[str, Any]]:
        """
        Automatically extract important facts from conversations.
        Uses pattern matching to identify preferences, facts, and instructions.
        """
        extracted = []

        # Pattern: "I prefer X" / "I like X" / "I use X"
        preference_patterns = [
            (r"(?:i prefer|i like|i use|i work with|my favorite is)\s+(.+?)(?:\.|$|,)", "preference"),
            (r"(?:i am|i'm|my name is)\s+(.+?)(?:\.|$|,)", "fact"),
            (r"(?:always|never|please always|please never)\s+(.+?)(?:\.|$|,)", "instruction"),
            (r"(?:my project|i'm working on|i'm building)\s+(.+?)(?:\.|$|,)", "project"),
        ]

        for pattern, category in preference_patterns:
            matches = re.findall(pattern, message.lower())
            for match in matches:
                match = match.strip()
                if len(match) > 3 and len(match) < 200:
                    key = f"auto_{category}_{hash(match) % 10000}"
                    memory = await self.store(
                        user_id=user_id,
                        key=key,
                        value=match,
                        category=category,
                        importance=0.4,
                    )
                    extracted.append(memory)

        return extracted


# Singleton
memory_manager = MemoryManager()
