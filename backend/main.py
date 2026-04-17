"""
AI OS — Main Application Entry Point
FastAPI server with all routes, middleware, and lifecycle management.
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

# Fix Windows encoding for console output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings


# ── Lifecycle Events ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # ── STARTUP ──
    print("=" * 60)
    print("[*] AI OS Backend Starting...")
    print(f"    Environment: {settings.app_env}")
    print(f"    Debug: {settings.debug}")
    print(f"    Port: {settings.app_port}")
    print("=" * 60)

    # Initialize Supabase
    from services.supabase_client import db
    db.initialize(
        url=settings.supabase_url,
        key=settings.supabase_anon_key,
    )

    # Initialize Redis
    from services.redis_client import cache
    await cache.initialize(settings.redis_url)

    # Log API key status
    print("\n[+] API Key Status:")
    print(f"    Groq:      {'[OK] Configured' if settings.groq_api_key else '[!!] Missing'}")
    print(f"    OpenAI:    {'[OK] Configured' if settings.openai_api_key else '[--] Not set'}")
    print(f"    Anthropic: {'[OK] Configured' if settings.anthropic_api_key else '[--] Not set'}")
    print(f"    Supabase:  {'[OK] Configured' if settings.supabase_url and settings.supabase_url != 'YOUR_SUPABASE_PROJECT_URL' else '[>>] In-memory mode'}")
    print(f"    Redis:     {'[OK] Connected' if cache.is_connected else '[>>] In-memory mode'}")
    print("\n" + "=" * 60)
    print("[OK] AI OS Backend Ready!")
    print(f"    API Docs:  http://localhost:{settings.app_port}/docs")
    print(f"    Health:    http://localhost:{settings.app_port}/health")
    print("=" * 60 + "\n")

    yield

    # ── SHUTDOWN ──
    print("\n[*] Shutting down AI OS Backend...")
    from services.redis_client import cache
    await cache.close()
    print("[OK] Shutdown complete.")


# ── Create FastAPI App ──────────────────────────────────────────────

app = FastAPI(
    title="AI OS API",
    description=(
        "🧠 **AI OS — Unified AI Platform**\n\n"
        "One API to rule them all. Auto-routes your prompts to the best AI model, "
        "maintains persistent memory across sessions, and tracks usage by tier.\n\n"
        "**Features:**\n"
        "- 🧠 Smart Model Routing (Groq, OpenAI, Anthropic)\n"
        "- 💾 Persistent Memory System\n"
        "- ⚡ Multi-Step Workflow Automation\n"
        "- ✅ Fact-Checking & Source Citations\n"
        "- 📊 Usage Tracking & Cost Management\n"
        "- 🔐 JWT Authentication\n"
        "- ⚙️ Tier-Based Rate Limiting (Free/Pro/Enterprise)\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS Middleware ─────────────────────────────────────────────────

# In debug/development mode: allow ALL origins so any localhost port works.
# In production: restrict to the explicit CORS_ORIGINS list in .env.
if settings.debug:
    origins = ["*"]
    allow_credentials = False  # wildcard origin requires credentials=False
else:
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    allow_credentials = True  # safe once origins is a specific list

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routers ───────────────────────────────────────────────

from api.auth import router as auth_router
from api.chat import router as chat_router
from api.workflow import router as workflow_router
from api.memory import router as memory_router
from api.usage import router as usage_router
from api.waitlist import router as waitlist_router
from api.conversations import router as conversations_router

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(workflow_router)
app.include_router(memory_router)
app.include_router(usage_router)
app.include_router(waitlist_router)
app.include_router(conversations_router)


# ── Health Check ────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """System health check."""
    from services.redis_client import cache
    from services.supabase_client import db

    return {
        "status": "ok",
        "service": "AI OS Backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "redis": "connected" if cache.is_connected else "in-memory",
            "database": "connected" if db.is_connected else "in-memory",
            "groq": "configured" if settings.groq_api_key else "missing",
        },
    }


@app.get("/", tags=["System"])
async def root():
    """API root — redirects to docs."""
    return {
        "message": "🧠 AI OS Backend API",
        "version": "1.0.0",
        "docs": f"http://localhost:{settings.app_port}/docs",
        "health": f"http://localhost:{settings.app_port}/health",
        "endpoints": {
            "auth": "/api/auth/register, /api/auth/login",
            "chat": "POST /api/chat",
            "memory": "GET/POST /api/memory",
            "workflow": "POST /api/workflow",
            "usage": "GET /api/usage",
            "waitlist": "POST /api/waitlist",
        },
    }


# ── Global Exception Handler ───────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a clean error."""
    if isinstance(exc, HTTPException):
        raise exc

    print(f"[ERROR] Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "Something went wrong",
        },
    )


# ── Run directly ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
