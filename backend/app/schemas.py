"""Pydantic models for API schemas."""
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ===== Search Models =====

class SearchRequest(BaseModel):
    """Restaurant search request."""
    query: str = Field(..., description="Search query (e.g., 'Keto Bowl', 'Biryani')")
    location: str = Field(..., description="Delivery location (e.g., 'Indiranagar')")
    cuisine: Optional[str] = Field(None, description="Cuisine filter")
    max_delivery_mins: Optional[int] = Field(None, description="Maximum delivery time")
    budget_cap_inr: Optional[float] = Field(None, description="Maximum budget per item")
    group_size: Optional[int] = Field(1, description="Number of people in group order")
    dietary_constraints: Optional[list[str]] = Field(None, description="Dietary constraints")


class MenuItemResult(BaseModel):
    """Menu item returned by the Zomato MCP server."""
    item_id: str
    name: str
    price_inr: float
    tags: list[str] = []
    detail: str = ""


class RestaurantResult(BaseModel):
    """Restaurant search result."""
    restaurant_id: str
    name: str
    cuisine: str
    location: str
    rating: float
    eta_mins: int
    delivery_fee_inr: float
    tags: list[str]
    image_url: Optional[str] = None
    menu_items: list[MenuItemResult] = []


class MealPlan(BaseModel):
    """Plan produced by the routed model before Zomato search."""
    keyword: str
    dietary_constraints: list[str] = []
    budget_cap_inr: Optional[float] = None
    max_delivery_mins: Optional[int] = None
    rationale: str = ""
    model: str


class DietaryReview(BaseModel):
    """Menu items the model kept after checking them against the live menu."""
    item_ids: list[str] = []
    notes: str = ""
    allergen_flags: list[str] = []
    model: str = ""


class EvalScore(BaseModel):
    """Scores for one search. Groundedness is capped by ids that exist."""
    groundedness: float
    dietary_fit: float
    safety: float
    notes: str = ""
    model: str = ""


class SearchResponse(BaseModel):
    """Restaurant search response."""
    restaurants: list[RestaurantResult]
    menu_items: list[MenuItemResult] = []
    session_id: Optional[str] = None
    execution_time_ms: float
    model_used: str
    cost_usd: float = 0
    plan: Optional[MealPlan] = None
    dietary_review: Optional[DietaryReview] = None
    evaluation: Optional[EvalScore] = None
    llm_error: Optional[str] = None


class EvalJudgeRequest(BaseModel):
    """Score one finished search without reading the database."""
    query: str
    dietary_constraints: list[str] = []
    restaurants: list[RestaurantResult] = []
    menu_items: list[MenuItemResult] = []
    selected_item_ids: list[str] = []


# ===== Agent Trajectory Models =====

class AgentStep(BaseModel):
    """Single agent execution step."""
    agent_type: Literal["lead", "worker"]
    worker_id: Optional[str] = None
    step_number: int
    tool_name: str
    tool_arguments: dict[str, Any]
    tool_result: dict[str, Any]
    status: Literal["success", "error", "pending"]
    execution_time_ms: float
    model_used: str
    cost_usd: float


class AgentTrajectoryResponse(BaseModel):
    """Agent execution trajectory."""
    session_id: str
    user_prompt: str
    steps: list[AgentStep]
    total_execution_time_ms: float
    total_cost_usd: float
    status: Literal["completed", "error", "in_progress"]


# ===== Cart Models =====

class CartItem(BaseModel):
    """Cart item with customizations."""
    item_id: str
    name: str
    quantity: int
    price_inr: float
    customizations: Optional[dict[str, Any]] = None
    tags: list[str] = []


class DeliveryAddress(BaseModel):
    """Delivery address details."""
    street: str
    area: str
    city: str
    pincode: str
    landmark: Optional[str] = None


class BuildCartRequest(BaseModel):
    """Cart build request."""
    session_id: str
    restaurant_id: str
    items: list[CartItem]
    delivery_address: DeliveryAddress
    promo_code: Optional[str] = None


class CartResponse(BaseModel):
    """Cart response."""
    cart_id: str
    session_id: str
    restaurant_id: str
    restaurant_name: str
    items: list[CartItem]
    subtotal_inr: float
    discount_inr: float
    delivery_fee_inr: float
    platform_fee_inr: float
    total_inr: float
    promo_code: Optional[str] = None
    status: Literal["staged", "approved", "rejected", "placed"]
    created_at: datetime


class ApproveCartRequest(BaseModel):
    """Cart approval request."""
    cart_id: str
    allergen_confirmed: bool = Field(..., description="User confirmed allergen safety")


class ApproveCartResponse(BaseModel):
    """Cart approval response."""
    cart_id: str
    status: Literal["approved", "rejected"]
    message: str
    order_token: Optional[str] = None


# ===== Evaluation Models =====

class EvalCaseResponse(BaseModel):
    """Single evaluation case."""
    id: str
    slice: str
    eval_type: str
    user_prompt: str
    mcp_tools_required: list[str]
    expected_constraints: dict[str, Any]
    ground_truth_schema: Optional[dict[str, Any]] = None
    eval_rubric: Optional[dict[str, Any]] = None


class EvalResultResponse(BaseModel):
    """Evaluation result."""
    eval_case_id: str
    session_id: str
    groundedness_score: float
    safety_score: float
    allergen_check_passed: bool
    prompt_injection_detected: bool
    execution_time_ms: float
    total_cost_usd: float
    status: Literal["pass", "fail"]
    failure_reason: Optional[str] = None
    created_at: datetime


class EvalSummaryResponse(BaseModel):
    """Evaluation summary statistics."""
    total_cases: int
    passed: int
    failed: int
    avg_groundedness: float
    avg_safety: float
    avg_execution_time_ms: float
    total_cost_usd: float


# ===== Error Models =====

class ErrorResponse(BaseModel):
    """Standard error response."""
    status: Literal["error"]
    code: str
    message: str
    details: Optional[dict[str, Any]] = None
