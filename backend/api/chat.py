"""
AI OS — Chat API Route
The main unified chat endpoint. Auto-routes to the best model,
injects user memory, tracks costs, and optionally fact-checks.
"""

import uuid
import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from models.conversation import ChatRequest, ChatResponse
from core.model_router import router as model_router
from core.litellm_client import llm_client
from core.memory_manager import memory_manager
from core.fact_checker import fact_checker
from middleware.auth_middleware import get_current_user
from middleware.rate_limiter import check_rate_limit
from middleware.usage_tracker import track_usage
from services.supabase_client import db
from utils.helpers import generate_title

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def unified_chat(
    request: ChatRequest,
    user: Dict = Depends(get_current_user),
):
    """
    🧠 Unified Chat Endpoint

    The core of AI OS. Send a message and it:
    1. Checks rate limits for your tier
    2. Loads your persistent memory context
    3. Auto-routes to the best AI model
    4. Streams the response
    5. Tracks usage & costs
    6. Auto-extracts memories
    7. Optionally fact-checks the response

    Body:
      - messages: [{role: "user", content: "..."}]
      - conversation_id: optional, to continue a conversation
      - model: optional, override auto-routing
      - stream: false (streaming not yet exposed via REST)
      - include_memory: true (inject user context)
      - fact_check: false (add confidence scores)
    """
    user_id = user["id"]
    user_tier = user.get("tier", "free")

    # ── 1. Rate Limit Check ─────────────────────────────────────
    await check_rate_limit(user_id, user_tier)

    # ── 2. Load User Memory Context ──────────────────────────────
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if request.include_memory:
        memory_context = await memory_manager.get_context_prompt(user_id)
        if memory_context:
            # Prepend memory as a system message
            system_msg = {
                "role": "system",
                "content": (
                    "You are AI OS, a unified AI assistant. Be helpful, accurate, and concise.\n\n"
                    f"{memory_context}\n\n"
                    "Use the above context to personalize your responses when relevant."
                ),
            }
            messages.insert(0, system_msg)
        else:
            messages.insert(0, {
                "role": "system",
                "content": "You are AI OS, a unified AI assistant. Be helpful, accurate, and concise.",
            })

    # ── 3. Route to Best Model ───────────────────────────────────
    last_message = request.messages[-1].content if request.messages else ""
    model, routing_reason = model_router.route(
        message=last_message,
        user_tier=user_tier,
        preferred_model=request.model,
    )

    # ── 4. Call the AI Model ─────────────────────────────────────
    max_tokens = request.max_tokens or 4096
    ai_result = await llm_client.chat(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=request.temperature or 0.7,
        stream=False,
        user_id=user_id,
    )

    # ── 5. Track Usage & Cost ────────────────────────────────────
    await track_usage(
        user_id=user_id,
        endpoint="/api/chat",
        model=model,
        tokens_input=ai_result["tokens_input"],
        tokens_output=ai_result["tokens_output"],
        cost=ai_result["cost"],
    )

    # ── 6. Manage Conversation ───────────────────────────────────
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Create/update conversation record
    existing_conv = await db.select_one("conversations", {"id": conversation_id})
    if not existing_conv:
        await db.insert("conversations", {
            "id": conversation_id,
            "user_id": user_id,
            "title": generate_title(last_message),
            "model_used": model,
        })

    # Save user message
    await db.insert("messages", {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "role": "user",
        "content": last_message,
    })

    # Save assistant response
    await db.insert("messages", {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": ai_result["content"],
        "model": model,
        "tokens_used": ai_result["total_tokens"],
        "cost": ai_result["cost"],
    })

    # ── 7. Auto-Extract Memories ─────────────────────────────────
    try:
        await memory_manager.auto_extract_memories(
            user_id=user_id,
            message=last_message,
            response=ai_result["content"],
        )
    except Exception:
        pass  # Memory extraction is best-effort

    # ── 8. Fact Check (if requested) ─────────────────────────────
    confidence = None
    sources = None
    if request.fact_check:
        fact_result = fact_checker.analyze(ai_result["content"])
        confidence = fact_result["confidence"]
        sources = fact_result.get("sources_suggested")

    # ── 9. Build Response ────────────────────────────────────────
    return ChatResponse(
        conversation_id=conversation_id,
        model_used=model,
        content=ai_result["content"],
        tokens_input=ai_result["tokens_input"],
        tokens_output=ai_result["tokens_output"],
        cost=ai_result["cost"],
        confidence=confidence,
        sources=sources,
        routing_reason=routing_reason,
    )


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    user: Dict = Depends(get_current_user),
):
    """
    🌊 Streaming Chat Endpoint (SSE)

    Same pipeline as /api/chat but streams the AI response token-by-token
    using Server-Sent Events. Use EventSource or fetch with ReadableStream
    on the frontend.

    Each chunk: `data: <token_text>`
    Final chunk: `data: [DONE]`
    """
    user_id = user["id"]
    user_tier = user.get("tier", "free")

    # Rate limit
    await check_rate_limit(user_id, user_tier)

    # Build messages
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    # Inject memory
    if request.include_memory:
        memory_context = await memory_manager.get_context_prompt(user_id)
        system_content = "You are AI OS, a unified AI assistant. Be helpful, accurate, and concise."
        if memory_context:
            system_content += f"\n\n{memory_context}\n\nUse the above context to personalize your responses when relevant."
        messages.insert(0, {"role": "system", "content": system_content})

    # Route model
    last_message = request.messages[-1].content if request.messages else ""
    model, _ = model_router.route(
        message=last_message,
        user_tier=user_tier,
        preferred_model=request.model,
    )

    # Prepare conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def event_generator():
        full_content = ""
        try:
            async for token in llm_client.stream_chat_generator(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens or 4096,
                temperature=request.temperature or 0.7,
            ):
                full_content += token
                # SSE format
                yield f"data: {json.dumps({'token': token, 'conversation_id': conversation_id, 'model': model})}\n\n"

            # Save conversation after streaming completes
            existing_conv = await db.select_one("conversations", {"id": conversation_id})
            if not existing_conv:
                await db.insert("conversations", {
                    "id": conversation_id,
                    "user_id": user_id,
                    "title": generate_title(last_message),
                    "model_used": model,
                })

            await db.insert("messages", {
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "role": "user",
                "content": last_message,
            })

            # Estimate tokens for streamed response
            tokens_input_est = int(len(" ".join(m["content"] for m in messages).split()) * 1.3)
            tokens_output_est = int(len(full_content.split()) * 1.3)
            cost_est = llm_client._calculate_cost(model, tokens_input_est, tokens_output_est)

            await db.insert("messages", {
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": full_content,
                "model": model,
                "tokens_used": tokens_output_est,
                "cost": cost_est,
            })

            # Track usage so daily limits and analytics work
            try:
                await track_usage(
                    user_id=user_id,
                    endpoint="/api/chat/stream",
                    model=model,
                    tokens_input=tokens_input_est,
                    tokens_output=tokens_output_est,
                    cost=cost_est,
                )
            except Exception:
                pass

            # Best-effort memory extraction
            try:
                await memory_manager.auto_extract_memories(
                    user_id=user_id,
                    message=last_message,
                    response=full_content,
                )
            except Exception:
                pass

            # Send final metadata chunk so frontend can update cost/token display
            yield f"data: {json.dumps({'done': True, 'conversation_id': conversation_id, 'model': model, 'tokens_output': tokens_output_est, 'cost': cost_est})}\n\n"
            yield f"data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield f"data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models")
async def list_models(user: Dict = Depends(get_current_user)):
    """List available models for the user's tier."""
    user_tier = user.get("tier", "free")
    models = model_router.get_available_models(user_tier)
    return {"tier": user_tier, "models": models}
