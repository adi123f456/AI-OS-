"""
AI OS — Intelligent Model Router
Analyzes user input and selects the optimal AI model for the task.
Uses keyword analysis, message complexity scoring, and task classification.
"""

import re
from typing import Optional, Dict, List, Tuple
from config import MODEL_REGISTRY, TIER_LIMITS, settings


# ── Task Categories & Keywords ──────────────────────────────────────
TASK_PATTERNS = {
    "creative_writing": {
        "keywords": [
            "write", "story", "poem", "creative", "fiction", "novel",
            "essay", "blog", "article", "script", "lyrics", "narrative",
            "compose", "draft", "rewrite", "paraphrase",
        ],
        "priority_model": "groq/llama-3.3-70b-versatile",
        "fallback_model": "groq/gemma2-9b-it",
    },
    "code": {
        "keywords": [
            "code", "function", "debug", "program", "python", "javascript",
            "api", "class", "algorithm", "sql", "html", "css", "react",
            "backend", "frontend", "deploy", "git", "error", "bug",
            "refactor", "optimize", "compile", "syntax", "regex",
        ],
        "priority_model": "groq/llama-3.3-70b-versatile",
        "fallback_model": "groq/mixtral-8x7b-32768",
    },
    "reasoning": {
        "keywords": [
            "analyze", "compare", "explain", "logic", "math", "calculate",
            "evaluate", "reasoning", "prove", "derive", "deduce",
            "problem", "solve", "strategy", "critical", "think",
        ],
        "priority_model": "groq/llama-3.3-70b-versatile",
        "fallback_model": "groq/mixtral-8x7b-32768",
    },
    "summarization": {
        "keywords": [
            "summarize", "summary", "tldr", "brief", "condense",
            "key points", "overview", "outline", "recap", "digest",
        ],
        "priority_model": "groq/gemma2-9b-it",
        "fallback_model": "groq/llama-3.1-8b-instant",
    },
    "translation": {
        "keywords": [
            "translate", "translation", "convert to", "in spanish",
            "in french", "in hindi", "in german", "in japanese",
            "in chinese", "multilingual", "language",
        ],
        "priority_model": "groq/llama-3.3-70b-versatile",
        "fallback_model": "groq/mixtral-8x7b-32768",
    },
    "quick_answer": {
        "keywords": [
            "what is", "who is", "when", "where", "how to", "define",
            "meaning", "quick", "short answer", "yes or no",
        ],
        "priority_model": "groq/llama-3.1-8b-instant",
        "fallback_model": "groq/gemma2-9b-it",
    },
    "research": {
        "keywords": [
            "research", "investigate", "deep dive", "comprehensive",
            "in-depth", "thorough", "detailed analysis", "study",
            "findings", "report", "literature", "survey",
        ],
        "priority_model": "groq/llama-3.3-70b-versatile",
        "fallback_model": "groq/mixtral-8x7b-32768",
    },
    "data_analysis": {
        "keywords": [
            "data", "csv", "json", "table", "chart", "graph",
            "statistics", "average", "median", "correlation",
            "dataset", "parse", "extract", "format",
        ],
        "priority_model": "groq/mixtral-8x7b-32768",
        "fallback_model": "groq/llama-3.3-70b-versatile",
    },
}


class ModelRouter:
    """
    Intelligent model routing engine.
    Analyzes user prompts and routes to the optimal model.
    """

    def __init__(self):
        self.model_registry = MODEL_REGISTRY
        self.task_patterns = TASK_PATTERNS

    def route(
        self,
        message: str,
        user_tier: str = "free",
        preferred_model: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Tuple[str, str]:
        """
        Route a message to the best model.

        Args:
            message: The user's message
            user_tier: free, pro, or enterprise
            preferred_model: User's explicit model choice (overrides auto-routing)
            conversation_history: Previous messages for context

        Returns:
            Tuple of (model_name, routing_reason)
        """
        # If user explicitly requested a model, use it (if allowed)
        if preferred_model:
            if self._is_model_allowed(preferred_model, user_tier):
                return preferred_model, f"User selected: {preferred_model}"
            else:
                return self._get_default_model(user_tier), f"Requested model '{preferred_model}' not available on {user_tier} tier"

        # Classify the task
        task_type, confidence = self._classify_task(message)

        # Get the best model for this task
        model, reason = self._select_model(task_type, confidence, user_tier, message)

        return model, reason

    def _classify_task(self, message: str) -> Tuple[str, float]:
        """
        Classify the task type based on keyword matching.
        Returns (task_type, confidence_score).
        """
        message_lower = message.lower()
        scores: Dict[str, float] = {}

        for task_type, config in self.task_patterns.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    # Longer keyword matches get higher scores
                    score += len(keyword.split()) * 1.5
            scores[task_type] = score

        if not scores or max(scores.values()) == 0:
            return "general", 0.3

        best_task = max(scores, key=scores.get)
        max_score = scores[best_task]

        # Normalize confidence (0.0 - 1.0)
        confidence = min(1.0, max_score / 10.0)

        return best_task, confidence

    def _select_model(
        self,
        task_type: str,
        confidence: float,
        user_tier: str,
        message: str,
    ) -> Tuple[str, str]:
        """Select the best model for the classified task within tier constraints."""

        # Get tier limits
        tier_config = TIER_LIMITS.get(user_tier, TIER_LIMITS["free"])
        allowed_models = tier_config["allowed_models"]

        # Check message complexity
        complexity = self._estimate_complexity(message)

        # Get candidate model from task patterns
        if task_type in self.task_patterns:
            pattern = self.task_patterns[task_type]
            candidate = pattern["priority_model"]
            fallback = pattern["fallback_model"]

            # Check if the candidate is allowed for this tier
            if self._is_model_allowed(candidate, user_tier):
                reason = f"Auto-routed to {self._get_display_name(candidate)} for {task_type} (confidence: {confidence:.0%})"
                return candidate, reason

            # Try fallback
            if self._is_model_allowed(fallback, user_tier):
                reason = f"Routed to {self._get_display_name(fallback)} (fallback for {task_type})"
                return fallback, reason

        # Default: use complexity-based routing
        if complexity == "simple":
            model = "groq/llama-3.1-8b-instant"
        elif complexity == "complex":
            model = "groq/llama-3.3-70b-versatile"
        else:
            model = "groq/gemma2-9b-it"

        if not self._is_model_allowed(model, user_tier):
            model = self._get_default_model(user_tier)

        reason = f"Auto-routed to {self._get_display_name(model)} based on complexity: {complexity}"
        return model, reason

    def _estimate_complexity(self, message: str) -> str:
        """
        Estimate message complexity based on length and structure.
        Returns: 'simple', 'medium', or 'complex'
        """
        word_count = len(message.split())

        # Check for multi-part requests
        has_multiple_parts = any(marker in message.lower() for marker in [
            "and then", "after that", "also", "additionally",
            "1.", "2.", "step 1", "first,", "second,",
        ])

        if word_count < 15 and not has_multiple_parts:
            return "simple"
        elif word_count > 100 or has_multiple_parts:
            return "complex"
        return "medium"

    def _is_model_allowed(self, model: str, user_tier: str) -> bool:
        """Check if a model is available for the user's tier."""
        tier_config = TIER_LIMITS.get(user_tier, TIER_LIMITS["free"])
        allowed = tier_config["allowed_models"]
        return "*" in allowed or model in allowed

    def _get_default_model(self, user_tier: str) -> str:
        """Get the default model for a tier."""
        tier_config = TIER_LIMITS.get(user_tier, TIER_LIMITS["free"])
        allowed = tier_config["allowed_models"]
        if allowed and allowed[0] != "*":
            return allowed[0]
        return "groq/llama-3.3-70b-versatile"

    def _get_display_name(self, model: str) -> str:
        """Get human-readable name for a model."""
        if model in self.model_registry:
            return self.model_registry[model]["display_name"]
        return model

    def get_available_models(self, user_tier: str) -> List[Dict]:
        """Get list of available models for a tier with metadata."""
        tier_config = TIER_LIMITS.get(user_tier, TIER_LIMITS["free"])
        allowed = tier_config["allowed_models"]

        models = []
        for model_id, meta in self.model_registry.items():
            if "*" in allowed or model_id in allowed:
                models.append({
                    "id": model_id,
                    "name": meta["display_name"],
                    "provider": meta["provider"],
                    "strengths": meta["strengths"],
                    "speed": meta["speed"],
                })
        return models


# Singleton
router = ModelRouter()
