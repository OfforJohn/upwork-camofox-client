"""HTTP/JSON-RPC transport layer for Upwork Camofox client."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import sys
import os

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'packages'))

from domain_actions import ActionRunner, ActionEnvelope, ActionType, ActionResult


app = FastAPI(title="Upwork Camofox Client API", version="0.1.0")

# Global action runner instance
action_runner = ActionRunner()


class ActionRequest(BaseModel):
    """Action request model."""
    type: str = Field(..., description="Action type (e.g., 'jobs.search')")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action payload")
    account_id: str = Field(..., description="Account ID for session scoping")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")


class ActionResponse(BaseModel):
    """Action response model."""
    action_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    events: List[Dict[str, Any]] = Field(default_factory=list)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "upwork-camofox-client",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/actions", response_model=ActionResponse)
async def execute_action(request: ActionRequest):
    """
    Execute an action through the vertical slice pipeline.
    
    This is a thin HTTP/JSON-RPC transport layer that:
    - Validates action envelope
    - Dispatches to ActionRunner
    - Returns typed results
    
    It does NOT contain:
    - Browser selectors
    - Cookie loading
    - Proxy setup
    - AsyncCamoufox integration
    
    All browser ownership stays in domain_camofox.
    """
    try:
        # Validate action type
        try:
            action_type = ActionType(request.type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action type: {request.type}. Valid types: {[t.value for t in ActionType]}"
            )
        
        # Create action envelope
        action = ActionEnvelope(
            type=action_type,
            payload=request.payload,
            account_id=request.account_id,
            correlation_id=request.correlation_id,
        )
        
        # Execute action through runner
        result = await action_runner.execute(action)
        
        # Return typed response
        return ActionResponse(
            action_id=result.action_id,
            success=result.success,
            data=result.data,
            error=result.error,
            events=[e.to_dict() for e in result.events],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/actions/jobs.search", response_model=ActionResponse)
async def jobs_search(request: ActionRequest):
    """Convenience endpoint for jobs.search action."""
    request.type = "jobs.search"
    return await execute_action(request)


@app.post("/actions/jobs.get", response_model=ActionResponse)
async def jobs_get(request: ActionRequest):
    """Convenience endpoint for jobs.get action."""
    request.type = "jobs.get"
    return await execute_action(request)


@app.post("/actions/proposals.draft", response_model=ActionResponse)
async def proposals_draft(request: ActionRequest):
    """Convenience endpoint for proposals.draft action."""
    request.type = "proposals.draft"
    return await execute_action(request)


@app.post("/actions/proposals.submit", response_model=ActionResponse)
async def proposals_submit(request: ActionRequest):
    """Convenience endpoint for proposals.submit action."""
    request.type = "proposals.submit"
    return await execute_action(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
