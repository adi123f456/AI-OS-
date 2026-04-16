"""
AI OS — Workflow API Route
Multi-step AI automation pipelines.
"""

from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException

from models.workflow import WorkflowCreate, WorkflowResponse
from core.workflow_engine import workflow_engine
from middleware.auth_middleware import get_current_user
from middleware.rate_limiter import check_rate_limit
from config import TIER_LIMITS

router = APIRouter(prefix="/api/workflow", tags=["Workflows"])


@router.post("", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowCreate,
    user: Dict = Depends(get_current_user),
):
    """
    🔄 Execute a multi-step AI workflow.

    Chain multiple AI tasks together with template variables.
    Each step's output can be referenced in subsequent steps.

    Example:
    ```json
    {
      "name": "Blog Pipeline",
      "steps": [
        {"action": "research", "prompt": "Research {{topic}}"},
        {"action": "write", "prompt": "Write article using: {{step_1_output}}"},
        {"action": "summarize", "prompt": "Create tweets from: {{step_2_output}}"}
      ],
      "variables": {"topic": "AI trends 2026"}
    }
    ```
    """
    user_id = user["id"]
    user_tier = user.get("tier", "free")

    # Check if workflows are allowed for this tier
    tier_config = TIER_LIMITS.get(user_tier, TIER_LIMITS["free"])
    features = tier_config.get("features", [])
    if "workflows" not in features and "*" not in features:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Feature not available",
                "message": "Workflows are available on Pro and Enterprise tiers.",
                "upgrade_hint": "Upgrade to Pro for workflow automation.",
            },
        )

    # Rate limit check
    await check_rate_limit(user_id, user_tier)

    # Validate steps
    if not request.steps or len(request.steps) == 0:
        raise HTTPException(status_code=400, detail="Workflow must have at least one step")

    if len(request.steps) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 steps per workflow")

    # Execute the workflow
    try:
        result = await workflow_engine.execute(
            user_id=user_id,
            user_tier=user_tier,
            name=request.name,
            steps=[s.model_dump() for s in request.steps],
            variables=request.variables,
        )

        return WorkflowResponse(
            id=result["id"],
            name=result["name"],
            status=result["status"],
            steps_total=result["steps_total"],
            steps_completed=result["steps_completed"],
            results=result["results"],
            total_cost=result["total_cost"],
            total_tokens=result["total_tokens"],
            created_at=result.get("created_at", ""),
            updated_at=result.get("updated_at", ""),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    user: Dict = Depends(get_current_user),
):
    """Get workflow status and results."""
    result = await workflow_engine.get_workflow(workflow_id, user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return result


@router.get("")
async def list_workflows(
    user: Dict = Depends(get_current_user),
    limit: int = 20,
):
    """List user's workflows."""
    workflows = await workflow_engine.list_workflows(user["id"], limit)
    return {"workflows": workflows, "count": len(workflows)}
