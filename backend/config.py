"""
AI OS — Application Configuration
Loads environment variables and defines tier limits, model configs.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "AI-OS"
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:5500,http://localhost:5501,http://127.0.0.1:5500,http://127.0.0.1:5501,http://localhost:8080,null"

    # JWT
    jwt_secret: str = "aios-secret-change-this-in-production-2026"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 1440  # 24 hours

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI Provider Keys
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Rate Limits
    free_tier_daily_limit: int = 50
    free_tier_rpm: int = 5
    pro_tier_rpm: int = 60
    enterprise_tier_rpm: int = 120

    # Mode
    local_mode: bool = False
    ollama_base_url: str = "http://localhost:11434"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# ── Tier Configuration ──────────────────────────────────────────────
TIER_LIMITS = {
    "free": {
        "daily_requests": 50,
        "rpm": 5,
        "max_tokens_per_request": 4096,
        "allowed_models": [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/gemma2-9b-it",
            "groq/mixtral-8x7b-32768",
        ],
        "features": ["chat", "memory_basic"],
    },
    "pro": {
        "daily_requests": -1,  # unlimited
        "rpm": 60,
        "max_tokens_per_request": 8192,
        "allowed_models": [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/gemma2-9b-it",
            "groq/mixtral-8x7b-32768",
            "groq/llama-3.1-70b-versatile",
            "gpt-4",
            "gpt-4-turbo",
            "claude-3-opus-20240229",
            "dall-e-3",
        ],
        "features": ["chat", "memory_advanced", "workflows", "fact_check", "priority_routing"],
    },
    "enterprise": {
        "daily_requests": -1,  # unlimited
        "rpm": 120,
        "max_tokens_per_request": 32768,
        "allowed_models": ["*"],  # all models
        "features": ["*"],  # all features
    },
}

# ── Model Metadata ──────────────────────────────────────────────────
MODEL_REGISTRY = {
    "groq/llama-3.3-70b-versatile": {
        "provider": "groq",
        "display_name": "Llama 3.3 70B",
        "strengths": ["general", "reasoning", "creative_writing", "analysis"],
        "cost_per_1k_input": 0.00059,
        "cost_per_1k_output": 0.00079,
        "max_tokens": 32768,
        "speed": "fast",
    },
    "groq/llama-3.1-8b-instant": {
        "provider": "groq",
        "display_name": "Llama 3.1 8B Instant",
        "strengths": ["quick_answers", "simple_tasks", "translation"],
        "cost_per_1k_input": 0.00005,
        "cost_per_1k_output": 0.00008,
        "max_tokens": 8192,
        "speed": "ultra_fast",
    },
    "groq/mixtral-8x7b-32768": {
        "provider": "groq",
        "display_name": "Mixtral 8x7B",
        "strengths": ["code", "reasoning", "math", "multilingual"],
        "cost_per_1k_input": 0.00024,
        "cost_per_1k_output": 0.00024,
        "max_tokens": 32768,
        "speed": "fast",
    },
    "groq/gemma2-9b-it": {
        "provider": "groq",
        "display_name": "Gemma 2 9B",
        "strengths": ["summarization", "instruction_following"],
        "cost_per_1k_input": 0.00020,
        "cost_per_1k_output": 0.00020,
        "max_tokens": 8192,
        "speed": "fast",
    },
}


# Singleton settings instance
settings = Settings()
