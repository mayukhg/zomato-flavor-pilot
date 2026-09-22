"""Database models for FlavorPilot."""
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import JSON, String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""
    pass


class EvalCase(Base):
    """Golden dataset evaluation test case."""
    __tablename__ = "eval_cases"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    slice: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    eval_type: Mapped[str] = mapped_column(String(100), nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    mcp_tools_required: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    expected_constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    ground_truth_schema: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    eval_rubric: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AgentTrajectory(Base):
    """Agent execution trajectory log."""
    __tablename__ = "agent_trajectories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "lead" or "worker"
    worker_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_arguments: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tool_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # "success", "error", "pending"
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class EvalResult(Base):
    """Evaluation run results."""
    __tablename__ = "eval_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eval_case_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    groundedness_score: Mapped[float] = mapped_column(Float, nullable=False)
    safety_score: Mapped[float] = mapped_column(Float, nullable=False)
    allergen_check_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prompt_injection_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # "pass", "fail"
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Cart(Base):
    """Staged cart for order approval."""
    __tablename__ = "carts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    restaurant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    restaurant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    delivery_address: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    subtotal_inr: Mapped[float] = mapped_column(Float, nullable=False)
    discount_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    delivery_fee_inr: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee_inr: Mapped[float] = mapped_column(Float, nullable=False)
    total_inr: Mapped[float] = mapped_column(Float, nullable=False)
    promo_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="staged")  # "staged", "approved", "rejected", "placed"
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
