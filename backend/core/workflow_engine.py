"""
AI OS — Workflow Engine
Multi-step AI task automation. Chains multiple AI calls,
piping output from one step as input to the next.
"""

import re
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from core.model_router import router
from core.litellm_client import llm_client
from services.supabase_client import db


class WorkflowEngine:
    """
    Executes multi-step AI workflows.

    Example workflow:
    {
        "name": "Blog Post Pipeline",
        "steps": [
            {"action": "research", "prompt": "Research {{topic}}"},
            {"action": "write", "prompt": "Write article using: {{step_1_output}}"},
            {"action": "summarize", "prompt": "Create social posts from: {{step_2_output}}"}
        ],
        "variables": {"topic": "AI in healthcare"}
    }
    """

    async def execute(
        self,
        user_id: str,
        user_tier: str,
        name: str,
        steps: List[Dict[str, Any]],
        variables: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow.

        Args:
            user_id: The user's ID
            user_tier: User's subscription tier
            name: Workflow name
            steps: List of step definitions
            variables: User-defined template variables

        Returns:
            Workflow result with all step outputs
        """
        workflow_id = str(uuid.uuid4())
        variables = variables or {}
        results = []
        total_cost = 0.0
        total_tokens = 0

        # Save workflow to DB
        workflow_data = {
            "id": workflow_id,
            "user_id": user_id,
            "name": name,
            "steps": [dict(s) for s in steps],
            "status": "running",
            "results": [],
            "total_cost": 0.0,
            "total_tokens": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await db.insert("workflows", workflow_data)

        try:
            for i, step in enumerate(steps):
                step_num = i + 1

                # Resolve template variables in the prompt
                prompt = self._resolve_template(
                    step.get("prompt", ""),
                    variables,
                    results,
                )

                # Determine model
                model = step.get("model")
                if not model or model == "auto":
                    model, routing_reason = router.route(prompt, user_tier)
                else:
                    routing_reason = f"User specified: {model}"

                # Execute the AI call
                ai_result = await llm_client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=step.get("max_tokens", 4096),
                    temperature=step.get("temperature", 0.7),
                    user_id=user_id,
                )

                # Collect result
                step_result = {
                    "step": step_num,
                    "action": step.get("action", "custom"),
                    "model": model,
                    "routing_reason": routing_reason,
                    "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                    "output": ai_result["content"],
                    "tokens": ai_result["total_tokens"],
                    "cost": ai_result["cost"],
                    "latency_ms": ai_result["latency_ms"],
                }
                results.append(step_result)
                total_cost += ai_result["cost"]
                total_tokens += ai_result["total_tokens"]

                # Update workflow progress in DB
                await db.update(
                    "workflows",
                    {"id": workflow_id},
                    {
                        "results": results,
                        "total_cost": total_cost,
                        "total_tokens": total_tokens,
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                )

            # Mark as completed
            await db.update(
                "workflows",
                {"id": workflow_id},
                {"status": "completed", "updated_at": datetime.utcnow().isoformat()},
            )

            return {
                "id": workflow_id,
                "name": name,
                "status": "completed",
                "steps_total": len(steps),
                "steps_completed": len(results),
                "results": results,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
            }

        except Exception as e:
            # Mark as failed
            await db.update(
                "workflows",
                {"id": workflow_id},
                {
                    "status": "failed",
                    "results": results,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            raise Exception(f"Workflow failed at step {len(results) + 1}: {str(e)}")

    def _resolve_template(
        self,
        prompt: str,
        variables: Dict[str, str],
        previous_results: List[Dict],
    ) -> str:
        """
        Replace template variables in a prompt.
        Supports: {{variable_name}} and {{step_N_output}}
        """
        # Replace user-defined variables
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", value)

        # Replace step output references
        for i, result in enumerate(previous_results):
            step_num = i + 1
            prompt = prompt.replace(
                f"{{{{step_{step_num}_output}}}}",
                result.get("output", ""),
            )

        return prompt

    async def get_workflow(self, workflow_id: str, user_id: str) -> Optional[Dict]:
        """Get a workflow by ID."""
        return await db.select_one("workflows", {"id": workflow_id, "user_id": user_id})

    async def list_workflows(self, user_id: str, limit: int = 20) -> List[Dict]:
        """List workflows for a user."""
        return await db.select(
            "workflows",
            {"user_id": user_id},
            limit=limit,
            order_by="created_at",
            ascending=False,
        )


# Singleton
workflow_engine = WorkflowEngine()
