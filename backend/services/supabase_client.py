"""
AI OS — Supabase Client Service
Manages connection to Supabase for database operations.
Falls back to in-memory storage if Supabase is not configured.
"""

import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import uuid

# Try importing supabase
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class InMemoryStore:
    """Fallback in-memory database when Supabase is not configured."""

    def __init__(self):
        self.tables: Dict[str, List[Dict[str, Any]]] = {
            "users": [],
            "waitlist": [],
            "conversations": [],
            "messages": [],
            "user_memory": [],
            "usage_logs": [],
            "daily_usage": [],
            "workflows": [],
        }

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record into a table."""
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        if "created_at" not in data:
            data["created_at"] = datetime.utcnow().isoformat()
        self.tables.setdefault(table, []).append(data)
        return data

    def select(self, table: str, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Select records from a table with optional filters."""
        records = self.tables.get(table, [])
        if filters:
            for key, value in filters.items():
                records = [r for r in records if r.get(key) == value]
        return records[:limit]

    def select_one(self, table: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select a single record."""
        results = self.select(table, filters, limit=1)
        return results[0] if results else None

    def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update records matching filters."""
        records = self.tables.get(table, [])
        updated = None
        for record in records:
            match = all(record.get(k) == v for k, v in filters.items())
            if match:
                record.update(data)
                record["updated_at"] = datetime.utcnow().isoformat()
                updated = record
        return updated

    def delete(self, table: str, filters: Dict[str, Any]) -> bool:
        """Delete records matching filters."""
        records = self.tables.get(table, [])
        initial_count = len(records)
        self.tables[table] = [
            r for r in records
            if not all(r.get(k) == v for k, v in filters.items())
        ]
        return len(self.tables[table]) < initial_count

    def upsert(self, table: str, data: Dict[str, Any], conflict_key: str = "id") -> Dict[str, Any]:
        """Insert or update based on conflict key."""
        existing = self.select_one(table, {conflict_key: data.get(conflict_key)})
        if existing:
            return self.update(table, {conflict_key: data[conflict_key]}, data)
        return self.insert(table, data)


class SupabaseService:
    """
    Database service that uses Supabase when configured,
    falls back to in-memory storage for local development.
    """

    def __init__(self):
        self.client: Optional[Any] = None
        self.memory_store: Optional[InMemoryStore] = None
        self.is_connected = False

    def initialize(self, url: str = "", key: str = ""):
        """Initialize the database connection."""
        if url and key and url != "YOUR_SUPABASE_PROJECT_URL" and HAS_SUPABASE:
            try:
                self.client = create_client(url, key)
                self.is_connected = True
                print("[OK] Connected to Supabase")
            except Exception as e:
                print(f"[WARN] Supabase connection failed: {e}")
                print("[>>] Using in-memory storage")
                self.memory_store = InMemoryStore()
        else:
            print("[>>] Supabase not configured -- using in-memory storage")
            self.memory_store = InMemoryStore()

    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record."""
        if self.client:
            result = self.client.table(table).insert(data).execute()
            return result.data[0] if result.data else data
        return self.memory_store.insert(table, data)

    async def select(
        self,
        table: str,
        filters: Dict[str, Any] = None,
        limit: int = 100,
        order_by: str = None,
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """Select records."""
        if self.client:
            query = self.client.table(table).select("*")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            if order_by:
                query = query.order(order_by, desc=not ascending)
            query = query.limit(limit)
            result = query.execute()
            return result.data or []
        return self.memory_store.select(table, filters, limit)

    async def select_one(self, table: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select a single record."""
        results = await self.select(table, filters, limit=1)
        return results[0] if results else None

    async def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update records."""
        if self.client:
            query = self.client.table(table).update(data)
            for key, value in filters.items():
                query = query.eq(key, value)
            result = query.execute()
            return result.data[0] if result.data else None
        return self.memory_store.update(table, filters, data)

    async def delete(self, table: str, filters: Dict[str, Any]) -> bool:
        """Delete records."""
        if self.client:
            query = self.client.table(table).delete()
            for key, value in filters.items():
                query = query.eq(key, value)
            query.execute()
            return True
        return self.memory_store.delete(table, filters)

    async def upsert(self, table: str, data: Dict[str, Any], conflict_key: str = "id") -> Dict[str, Any]:
        """Insert or update."""
        if self.client:
            result = self.client.table(table).upsert(data).execute()
            return result.data[0] if result.data else data
        return self.memory_store.upsert(table, data, conflict_key)

    async def increment_daily_usage(self, user_id: str, tokens: int = 0, cost: float = 0.0):
        """Increment the daily usage counter for a user."""
        today = date.today().isoformat()
        existing = await self.select_one("daily_usage", {"user_id": user_id, "date": today})

        if existing:
            await self.update(
                "daily_usage",
                {"user_id": user_id, "date": today},
                {
                    "request_count": existing.get("request_count", 0) + 1,
                    "total_tokens": existing.get("total_tokens", 0) + tokens,
                    "total_cost": float(existing.get("total_cost", 0)) + cost,
                },
            )
        else:
            await self.insert(
                "daily_usage",
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "date": today,
                    "request_count": 1,
                    "total_tokens": tokens,
                    "total_cost": cost,
                },
            )

    async def get_daily_usage(self, user_id: str) -> Dict[str, Any]:
        """Get today's usage for a user."""
        today = date.today().isoformat()
        result = await self.select_one("daily_usage", {"user_id": user_id, "date": today})
        return result or {"request_count": 0, "total_tokens": 0, "total_cost": 0.0}


# Singleton instance
db = SupabaseService()
