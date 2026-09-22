"""Restaurant search endpoints."""
import time
import uuid
from fastapi import APIRouter, HTTPException

from backend.app.schemas import MenuItemResult, RestaurantResult, SearchRequest, SearchResponse
from backend.app.agents import LeadAgent

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search_restaurants(request: SearchRequest):
    """
    Search for restaurants matching criteria.
    
    Orchestrates Lead-Worker agents to find optimal restaurant matches
    based on dietary constraints, budget, and delivery requirements.
    """
    start_time = time.time()
    
    # Generate session ID
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    
    # Create lead agent
    lead_agent = LeadAgent(
        session_id=session_id,
        user_prompt=f"{request.query} in {request.location}"
    )
    
    try:
        # Execute agent orchestration
        result = await lead_agent.execute(
            query=request.query,
            location=request.location,
            budget_cap_inr=request.budget_cap_inr,
            group_size=request.group_size or 1,
            dietary_constraints=request.dietary_constraints,
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Search failed"))
        
        # Transform to response format
        restaurants = [
            RestaurantResult(**r) for r in result.get("restaurants", [])
        ]
        menu_items = [
            MenuItemResult(**item) for item in result.get("menu_items", [])
        ]
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            restaurants=restaurants,
            menu_items=menu_items,
            session_id=session_id,
            execution_time_ms=execution_time_ms,
            model_used=result.get("model_used", "unknown"),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search execution failed: {str(e)}")
