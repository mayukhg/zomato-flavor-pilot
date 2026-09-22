"""Evaluation endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func

from backend.app.llm import LLMClient, LLMNotConfigured
from backend.app.llm.client import route_model
from backend.app.schemas import (
    EvalCaseResponse,
    EvalJudgeRequest,
    EvalResultResponse,
    EvalScore,
    EvalSummaryResponse,
)
from backend.db import get_session
from backend.db.models import EvalCase, EvalResult

router = APIRouter()


@router.post("/judge", response_model=EvalScore)
async def judge_search(request: EvalJudgeRequest):
    """Score one search with the routed model. Does not place an order."""
    model = route_model(request.query, group_size=1)
    try:
        scores, _cost = await LLMClient().score(
            query=request.query,
            dietary_constraints=request.dietary_constraints,
            restaurants=[row.model_dump() for row in request.restaurants],
            menu_items=[item.model_dump() for item in request.menu_items],
            selected_item_ids=request.selected_item_ids,
            model=model,
        )
    except LLMNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Eval scoring failed: {error}") from error
    return EvalScore(**scores)


@router.get("/cases", response_model=list[EvalCaseResponse])
async def list_eval_cases(slice: Optional[str] = None, limit: int = 100):
    """
    List golden dataset evaluation cases.
    
    Args:
        slice: Optional filter by evaluation slice
        limit: Maximum number of cases to return
    """
    async with get_session() as session:
        query = select(EvalCase)
        
        if slice:
            query = query.where(EvalCase.slice == slice)
        
        query = query.limit(limit)
        
        result = await session.execute(query)
        cases = result.scalars().all()
        
        return [
            EvalCaseResponse(
                id=case.id,
                slice=case.slice,
                eval_type=case.eval_type,
                user_prompt=case.user_prompt,
                mcp_tools_required=case.mcp_tools_required,
                expected_constraints=case.expected_constraints,
                ground_truth_schema=case.ground_truth_schema,
                eval_rubric=case.eval_rubric,
            )
            for case in cases
        ]


@router.get("/results", response_model=list[EvalResultResponse])
async def list_eval_results(
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
):
    """
    List evaluation results.
    
    Args:
        session_id: Optional filter by session
        status: Optional filter by pass/fail status
        limit: Maximum number of results to return
    """
    async with get_session() as session:
        query = select(EvalResult)
        
        if session_id:
            query = query.where(EvalResult.session_id == session_id)
        
        if status:
            query = query.where(EvalResult.status == status)
        
        query = query.order_by(EvalResult.created_at.desc()).limit(limit)
        
        result = await session.execute(query)
        results = result.scalars().all()
        
        return [
            EvalResultResponse(
                eval_case_id=r.eval_case_id,
                session_id=r.session_id,
                groundedness_score=r.groundedness_score,
                safety_score=r.safety_score,
                allergen_check_passed=r.allergen_check_passed,
                prompt_injection_detected=r.prompt_injection_detected,
                execution_time_ms=r.execution_time_ms,
                total_cost_usd=r.total_cost_usd,
                status=r.status,
                failure_reason=r.failure_reason,
                created_at=r.created_at,
            )
            for r in results
        ]


@router.get("/summary", response_model=EvalSummaryResponse)
async def get_eval_summary():
    """
    Get evaluation summary statistics.
    
    Returns aggregate metrics across all evaluation runs.
    """
    async with get_session() as session:
        # Count total cases
        total_result = await session.execute(select(func.count()).select_from(EvalResult))
        total_cases = total_result.scalar() or 0
        
        # Count passed/failed
        passed_result = await session.execute(
            select(func.count()).select_from(EvalResult).where(EvalResult.status == "pass")
        )
        passed = passed_result.scalar() or 0
        failed = total_cases - passed
        
        # Calculate averages
        avg_result = await session.execute(
            select(
                func.avg(EvalResult.groundedness_score),
                func.avg(EvalResult.safety_score),
                func.avg(EvalResult.execution_time_ms),
                func.sum(EvalResult.total_cost_usd),
            )
        )
        row = avg_result.one_or_none()
        
        if row:
            avg_groundedness, avg_safety, avg_time, total_cost = row
        else:
            avg_groundedness = avg_safety = avg_time = total_cost = 0.0
        
        return EvalSummaryResponse(
            total_cases=total_cases,
            passed=passed,
            failed=failed,
            avg_groundedness=float(avg_groundedness or 0.0),
            avg_safety=float(avg_safety or 0.0),
            avg_execution_time_ms=float(avg_time or 0.0),
            total_cost_usd=float(total_cost or 0.0),
        )
