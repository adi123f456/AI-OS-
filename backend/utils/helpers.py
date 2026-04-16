"""
AI OS — Common Helper Utilities
"""

import re
import hashlib
from typing import Optional


def truncate(text: str, max_length: int = 200) -> str:
    """Truncate text to a maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def generate_title(message: str) -> str:
    """Generate a conversation title from the first message."""
    # Clean and truncate
    title = re.sub(r'\s+', ' ', message).strip()
    title = truncate(title, 80)
    return title or "New Conversation"


def content_hash(content: str) -> str:
    """Generate a hash for content (used for caching)."""
    return hashlib.md5(content.encode()).hexdigest()


def validate_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def count_tokens_estimate(text: str) -> int:
    """Rough token count estimate (~1.3 tokens per word)."""
    return int(len(text.split()) * 1.3)
