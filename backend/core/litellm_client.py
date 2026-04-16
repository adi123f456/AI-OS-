"""
AI OS — LiteLLM Client
Unified interface to call any AI model via LiteLLM.
Handles streaming, cost tracking, error fallbacks, and local mode.
"""

import os
import json
import time
from typing import Optional, List, Dict, Any, AsyncGenerator
from config import settings, MODEL_REGISTRY

# Set API keys in environment before importing litellm
os.environ["GROQ_API_KEY"] = settings.groq_api_key
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

import litellm
from litellm import completion, acompletion

# Configure litellm
litellm.drop_params = True  # Drop unsupported params silently
litellm.set_verbose = settings.debug


class LiteLLMClient:
    """
    Unified AI model client powered by LiteLLM.
    Supports streaming, cost tracking, and automatic fallbacks.
    """

    def __init__(self):
        self.call_log: List[Dict] = []

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False,
        user_id: str = "",
    ) -> Dict[str, Any]:
        """
        Send a chat completion request.

        Args:
            model: LiteLLM model identifier (e.g. 'groq/llama-3.3-70b-versatile')
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0.0-1.0)
            stream: Whether to stream the response
            user_id: For tracking purposes

        Returns:
            Dict with content, tokens, cost, model info
        """
        start_time = time.time()

        try:
            if stream:
                return await self._stream_chat(model, messages, max_tokens, temperature, user_id)

            # Non-streaming completion
            response = await acompletion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            elapsed = time.time() - start_time

            # Extract response data
            content = response.choices[0].message.content or ""
            usage = response.usage
            tokens_input = usage.prompt_tokens if usage else 0
            tokens_output = usage.completion_tokens if usage else 0

            # Calculate cost
            cost = self._calculate_cost(model, tokens_input, tokens_output)

            result = {
                "content": content,
                "model": model,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "total_tokens": tokens_input + tokens_output,
                "cost": cost,
                "latency_ms": int(elapsed * 1000),
                "finish_reason": response.choices[0].finish_reason,
            }

            # Log the call
            self._log_call(model, user_id, result)

            return result

        except Exception as e:
            # Try fallback model
            fallback = self._get_fallback(model)
            if fallback and fallback != model:
                print(f"[WARN] Model {model} failed: {e}. Trying fallback: {fallback}")
                return await self.chat(
                    model=fallback,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False,
                    user_id=user_id,
                )
            raise Exception(f"AI model call failed: {str(e)}")

    async def _stream_chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        user_id: str,
    ) -> Dict[str, Any]:
        """Handle streaming response and collect full result."""
        start_time = time.time()
        full_content = ""
        tokens_input = 0
        tokens_output = 0

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content

                # Try to get usage from final chunk
                if hasattr(chunk, 'usage') and chunk.usage:
                    tokens_input = chunk.usage.prompt_tokens or 0
                    tokens_output = chunk.usage.completion_tokens or 0

            elapsed = time.time() - start_time

            # Estimate tokens if not provided
            if tokens_output == 0:
                tokens_output = len(full_content.split()) * 1.3  # rough estimate

            cost = self._calculate_cost(model, tokens_input, int(tokens_output))

            result = {
                "content": full_content,
                "model": model,
                "tokens_input": tokens_input,
                "tokens_output": int(tokens_output),
                "total_tokens": tokens_input + int(tokens_output),
                "cost": cost,
                "latency_ms": int(elapsed * 1000),
                "finish_reason": "stop",
            }

            self._log_call(model, user_id, result)
            return result

        except Exception as e:
            raise Exception(f"Streaming failed: {str(e)}")

    async def stream_chat_generator(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Yield streaming chunks for SSE responses.
        """
        try:
            response = await acompletion(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\n[ERROR: {str(e)}]"

    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost based on model pricing."""
        meta = MODEL_REGISTRY.get(model)
        if meta:
            input_cost = (tokens_input / 1000) * meta["cost_per_1k_input"]
            output_cost = (tokens_output / 1000) * meta["cost_per_1k_output"]
            return round(input_cost + output_cost, 6)

        # Fallback: try litellm's built-in cost tracking
        try:
            cost = litellm.completion_cost(
                model=model,
                prompt="x" * tokens_input,
                completion="x" * tokens_output,
            )
            return round(cost, 6)
        except:
            return 0.0

    def _get_fallback(self, model: str) -> Optional[str]:
        """Get a fallback model when the primary fails."""
        fallbacks = {
            "groq/llama-3.3-70b-versatile": "groq/mixtral-8x7b-32768",
            "groq/mixtral-8x7b-32768": "groq/llama-3.1-8b-instant",
            "groq/gemma2-9b-it": "groq/llama-3.1-8b-instant",
            "groq/llama-3.1-8b-instant": None,
            "gpt-4": "groq/llama-3.3-70b-versatile",
            "claude-3-opus-20240229": "groq/llama-3.3-70b-versatile",
        }
        return fallbacks.get(model)

    def _log_call(self, model: str, user_id: str, result: Dict):
        """Log the call for cost tracking."""
        self.call_log.append({
            "model": model,
            "user_id": user_id,
            "tokens_input": result["tokens_input"],
            "tokens_output": result["tokens_output"],
            "cost": result["cost"],
            "latency_ms": result["latency_ms"],
            "timestamp": time.time(),
        })

    def get_total_cost(self, user_id: str = None) -> float:
        """Get total cost for a user or all users."""
        logs = self.call_log
        if user_id:
            logs = [l for l in logs if l["user_id"] == user_id]
        return sum(l["cost"] for l in logs)


# Singleton
llm_client = LiteLLMClient()
