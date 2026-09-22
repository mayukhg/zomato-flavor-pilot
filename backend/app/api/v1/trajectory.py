"""Agent trajectory endpoints."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.app.schemas import AgentTrajectoryResponse, AgentStep
from backend.db import get_session
from backend.db.models import AgentTrajectory

router = APIRouter()


@router.get("/trajectory/{session_id}", response_model=AgentTrajectoryResponse)
async def get_agent_trajectory(session_id: str):
    """
    Retrieve agent execution trajectory for a session.
    
    Returns the complete Lead-Worker orchestration steps with
    timing, costs, and tool call details.
    """
    async with get_session() as session:
        # Query trajectories for session
        result = await session.execute(
            select(AgentTrajectory)
            .where(AgentTrajectory.session_id == session_id)
            .order_by(AgentTrajectory.step_number)
        )
        trajectories = result.scalars().all()
        
        if not trajectories:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Transform to response format
        steps = [
            AgentStep(
                agent_type=t.agent_type,
                worker_id=t.worker_id,
                step_number=t.step_number,
                tool_name=t.tool_name,
                tool_arguments=t.tool_arguments,
                tool_result=t.tool_result,
                status=t.status,
                execution_time_ms=t.execution_time_ms,
                model_used=t.model_used,
                cost_usd=t.cost_usd,
            )
            for t in trajectories
        ]
        
        total_time = sum(s.execution_time_ms for s in steps)
        total_cost = sum(s.cost_usd for s in steps)
        
        # Determine overall status
        has_error = any(s.status == "error" for s in steps)
        has_pending = any(s.status == "pending" for s in steps)
        
        if has_error:
            status = "error"
        elif has_pending:
            status = "in_progress"
        else:
            status = "completed"
        
        return AgentTrajectoryResponse(
            session_id=session_id,
            user_prompt=trajectories[0].user_prompt,
            steps=steps,
            total_execution_time_ms=total_time,
            total_cost_usd=total_cost,
            status=status,
        )
