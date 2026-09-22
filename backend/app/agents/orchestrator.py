"""Lead-Worker agent orchestration engine."""
import asyncio
import logging
import time
from typing import Any, Optional

from backend.app.mcp import ZomatoMCPClient
from backend.app.mcp.zomato_client import flatten_menu_items
from backend.app.config import settings
from backend.app.llm import LLMClient, LLMNotConfigured
from backend.db import get_session
from backend.db.models import AgentTrajectory

logger = logging.getLogger(__name__)


class AgentStep:
    """Single agent execution step."""
    
    def __init__(
        self,
        agent_type: str,
        step_number: int,
        tool_name: str,
        tool_arguments: dict[str, Any],
        worker_id: Optional[str] = None,
    ):
        self.agent_type = agent_type
        self.worker_id = worker_id
        self.step_number = step_number
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments
        self.tool_result: dict[str, Any] = {}
        self.status = "pending"
        self.execution_time_ms = 0.0
        self.model_used = ""
        self.cost_usd = 0.0


class WorkerAgent:
    """Worker agent for specialized tasks."""
    
    def __init__(
        self,
        worker_id: str,
        task: str,
        mcp_client: ZomatoMCPClient,
    ):
        self.worker_id = worker_id
        self.task = task
        self.mcp_client = mcp_client
        self.steps: list[AgentStep] = []
    
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute worker task based on specialization."""
        logger.info(f"Worker {self.worker_id} executing: {self.task}")
        
        if self.worker_id == "Worker 1":
            return await self._check_dietary_constraints(context)
        elif self.worker_id == "Worker 2":
            return await self._optimize_price_and_promos(context)
        elif self.worker_id == "Worker 3":
            return await self._check_delivery_eta(context)
        else:
            return {"status": "error", "message": f"Unknown worker: {self.worker_id}"}
    
    async def _check_dietary_constraints(self, context: dict[str, Any]) -> dict[str, Any]:
        """Worker 1: Verify dietary constraints and allergens."""
        start_time = time.time()
        
        restaurant_id = context.get("restaurant_id")
        dietary_constraints = context.get("dietary_constraints", [])
        
        step = AgentStep(
            agent_type="worker",
            worker_id=self.worker_id,
            step_number=len(self.steps) + 1,
            tool_name="get_menu",
            tool_arguments={
                "restaurant_id": restaurant_id,
                "dietary_filter": dietary_constraints[0] if dietary_constraints else None,
            },
        )
        
        try:
            menu_data = context.get("menu")
            if not menu_data:
                menu_data = await self.mcp_client.get_menu(
                    restaurant_id=restaurant_id,
                    dietary_filter=dietary_constraints[0] if dietary_constraints else None,
                )
            
            review = context.get("dietary_review") or {}
            judged = "item_ids" in review
            verified_ids = review.get("item_ids") or []
            notes = review.get("notes") or context.get("llm_error") or ""
            step.tool_result = {
                "menu_item_count": len(flatten_menu_items(menu_data)),
                "verified_item_ids": verified_ids,
                "notes": notes,
                "allergen_flags": review.get("allergen_flags") or [],
            }
            step.status = "success" if judged or not context.get("llm_error") else "error"
            step.model_used = review.get("model") or settings.smart_intern_model
            step.cost_usd = float(context.get("dietary_cost_usd") or 0)
            
            result = {
                "status": "success" if judged or not context.get("llm_error") else "error",
                "verified_items_count": len(verified_ids),
                "dietary_constraints_met": bool(verified_ids) if judged and dietary_constraints else not bool(context.get("llm_error")),
                "allergen_safe": not review.get("allergen_flags"),
                "verified_items": verified_ids[:3],
                "notes": notes,
            }
            
        except Exception as e:
            logger.error(f"Worker 1 failed: {e}")
            step.status = "error"
            result = {"status": "error", "message": str(e)}
        
        step.execution_time_ms = (time.time() - start_time) * 1000
        self.steps.append(step)
        
        return result
    
    async def _optimize_price_and_promos(self, context: dict[str, Any]) -> dict[str, Any]:
        """Worker 2: Find best promo codes and optimize pricing."""
        start_time = time.time()
        
        step = AgentStep(
            agent_type="worker",
            worker_id=self.worker_id,
            step_number=len(self.steps) + 1,
            tool_name="create_cart",
            tool_arguments={"promo_code": context.get("promo_code")},
        )
        
        try:
            # Promo codes belong on Zomato create_cart at checkout. Searching must
            # not invent cart ids or submit coupons against the live account.
            step.tool_result = {
                "status": "deferred",
                "message": "Promo codes are applied on the Zomato cart at checkout.",
            }
            step.status = "success"
            step.model_used = context.get("model_used") or settings.smart_intern_model
            step.cost_usd = 0
            
            result = {
                "status": "success",
                "best_promo_code": None,
                "discount_inr": 0,
                "promos_tested": 0,
            }
            
        except Exception as e:
            logger.error(f"Worker 2 failed: {e}")
            step.status = "error"
            result = {"status": "error", "message": str(e)}
        
        step.execution_time_ms = (time.time() - start_time) * 1000
        self.steps.append(step)
        
        return result
    
    async def _check_delivery_eta(self, context: dict[str, Any]) -> dict[str, Any]:
        """Worker 3: Verify delivery ETA and logistics."""
        start_time = time.time()
        
        restaurant_id = context.get("restaurant_id")
        max_eta_mins = context.get("max_delivery_mins", 30)
        
        step = AgentStep(
            agent_type="worker",
            worker_id=self.worker_id,
            step_number=len(self.steps) + 1,
            tool_name="search_restaurants",
            tool_arguments={"location": context.get("location", ""), "max_delivery_mins": max_eta_mins},
        )
        
        try:
            estimated_mins = int(context.get("eta_mins") or 0)
            delivery_fee = float(context.get("delivery_fee_inr") or 0)
            
            step.tool_result = {
                "restaurant_id": restaurant_id,
                "eta_mins": estimated_mins,
                "eta_within_limit": estimated_mins <= max_eta_mins if estimated_mins else False,
                "delivery_fee_inr": delivery_fee,
            }
            step.status = "success"
            step.model_used = context.get("model_used") or settings.smart_intern_model
            step.cost_usd = 0
            
            result = {
                "status": "success",
                "eta_mins": estimated_mins,
                "eta_within_limit": estimated_mins <= max_eta_mins if estimated_mins else False,
                "delivery_fee_inr": delivery_fee,
            }
            
        except Exception as e:
            logger.error(f"Worker 3 failed: {e}")
            step.status = "error"
            result = {"status": "error", "message": str(e)}
        
        step.execution_time_ms = (time.time() - start_time) * 1000
        self.steps.append(step)
        
        return result


class LeadAgent:
    """Lead agent orchestrating worker agents."""
    
    def __init__(self, session_id: str, user_prompt: str):
        self.session_id = session_id
        self.user_prompt = user_prompt
        self.steps: list[AgentStep] = []
        self.workers: list[WorkerAgent] = []
    
    def _determine_complexity(self) -> str:
        """Determine if query needs PhD Reasoner or Smart Intern."""
        # Use PhD Reasoner for complex group orders, Smart Intern for simple queries
        complexity_keywords = ["group", "team", "people", "allergy", "allergen", "constraints"]
        
        prompt_lower = self.user_prompt.lower()
        if any(keyword in prompt_lower for keyword in complexity_keywords):
            return settings.phd_reasoner_model
        return settings.smart_intern_model
    
    async def execute(
        self,
        query: str,
        location: str,
        budget_cap_inr: Optional[float] = None,
        group_size: int = 1,
        dietary_constraints: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Execute lead agent orchestration."""
        logger.info(f"Lead agent executing for session {self.session_id}")
        
        start_time = time.time()
        model_used = self._determine_complexity()
        llm = LLMClient()
        plan: Optional[dict[str, Any]] = None
        dietary_review: Optional[dict[str, Any]] = None
        evaluation: Optional[dict[str, Any]] = None
        llm_error: Optional[str] = None
        llm_cost = 0.0

        try:
            plan, plan_cost = await llm.plan(
                query=query,
                group_size=group_size,
                dietary_constraints=dietary_constraints,
                budget_cap_inr=budget_cap_inr,
                model=model_used,
            )
            llm_cost += plan_cost
        except LLMNotConfigured as error:
            llm_error = str(error)
            logger.warning(llm_error)
        except Exception as error:
            llm_error = f"Meal plan failed: {error}"
            logger.error(llm_error)

        plan_step = AgentStep(
            agent_type="lead",
            step_number=1,
            tool_name="plan_meal",
            tool_arguments={"query": query, "group_size": group_size},
        )
        plan_step.tool_result = plan or {"error": llm_error}
        plan_step.status = "success" if plan else "error"
        plan_step.model_used = model_used
        plan_step.cost_usd = llm_cost
        self.steps.append(plan_step)

        search_keyword = (plan or {}).get("keyword") or None
        search_budget = budget_cap_inr if budget_cap_inr is not None else (plan or {}).get("budget_cap_inr")
        active_constraints = dietary_constraints or (plan or {}).get("dietary_constraints") or []
        
        # Step 2: Lead searches restaurants
        search_step = AgentStep(
            agent_type="lead",
            step_number=2,
            tool_name="search_restaurants",
            tool_arguments={
                "query": query,
                "location": location,
                "budget_cap_inr": search_budget,
                "keyword": search_keyword,
            },
        )
        
        # Official Zomato MCP server. "http" in older configs meant the same host;
        # mcp-remote is the supported way to reach it.
        transport = settings.zomato_mcp_transport
        if transport == "http":
            transport = "stdio"
        mcp_client = ZomatoMCPClient(
            transport=transport,
            server_url=settings.zomato_mcp_server_url,
            stdio_cmd=settings.zomato_mcp_stdio_cmd,
        )
        
        try:
            await mcp_client.connect()
            
            # Execute restaurant search
            step_start = time.time()
            restaurants = await mcp_client.search_restaurants(
                query=query,
                location=location,
                budget_cap_inr=search_budget,
                keyword=search_keyword,
                max_delivery_mins=(plan or {}).get("max_delivery_mins"),
            )
            
            search_step.tool_result = {"restaurants": restaurants, "keyword": search_keyword}
            search_step.status = "success"
            search_step.model_used = model_used
            search_step.cost_usd = 0
            search_step.execution_time_ms = (time.time() - step_start) * 1000
            self.steps.append(search_step)

            menu: dict[str, Any] = {}
            menu_items: list[dict[str, Any]] = []
            selected_restaurant = restaurants[0] if restaurants else {}
            restaurant_id = selected_restaurant.get("restaurant_id")
            if restaurant_id:
                try:
                    menu = await mcp_client.get_menu(restaurant_id=restaurant_id)
                    menu_items = flatten_menu_items(menu) or list(selected_restaurant.get("menu_items") or [])
                except Exception as menu_error:
                    logger.warning("Menu fetch failed for %s: %s", restaurant_id, menu_error)
                    menu_items = list(selected_restaurant.get("menu_items") or [])
            if restaurants:
                restaurants[0]["menu_items"] = menu_items or list(restaurants[0].get("menu_items") or [])

            review_cost = 0.0
            if menu_items and llm_error is None:
                try:
                    dietary_review, review_cost = await llm.judge_menu(
                        query=query,
                        dietary_constraints=active_constraints,
                        menu_items=menu_items,
                        model=model_used,
                    )
                    llm_cost += review_cost
                    chosen = set(dietary_review["item_ids"])
                    matched = [item for item in menu_items if item["item_id"] in chosen]
                    if matched:
                        menu_items = matched
                except Exception as error:
                    llm_error = f"Dietary judgment failed: {error}"
                    logger.error(llm_error)

            if llm_error is None:
                try:
                    evaluation, score_cost = await llm.score(
                        query=query,
                        dietary_constraints=active_constraints,
                        restaurants=restaurants,
                        menu_items=menu_items,
                        selected_item_ids=[item["item_id"] for item in menu_items],
                        model=model_used,
                    )
                    llm_cost += score_cost
                except Exception as error:
                    llm_error = f"Eval scoring failed: {error}"
                    logger.error(llm_error)
            
            # If group order with constraints, spawn workers
            if group_size > 1 or dietary_constraints or active_constraints:
                context = {
                    "restaurant_id": restaurant_id,
                    "dietary_constraints": active_constraints,
                    "budget_cap_inr": search_budget,
                    "location": location,
                    "max_delivery_mins": (plan or {}).get("max_delivery_mins") or 30,
                    "menu": menu,
                    "eta_mins": selected_restaurant.get("eta_mins"),
                    "delivery_fee_inr": selected_restaurant.get("delivery_fee_inr"),
                    "dietary_review": dietary_review or {},
                    "dietary_cost_usd": review_cost if dietary_review else 0,
                    "llm_error": llm_error,
                    "model_used": model_used,
                }
                
                # Spawn worker agents in parallel
                worker_1 = WorkerAgent("Worker 1", "Dietary & allergens", mcp_client)
                worker_2 = WorkerAgent("Worker 2", "Price & promos", mcp_client)
                worker_3 = WorkerAgent("Worker 3", "Delivery & ETA", mcp_client)
                
                self.workers = [worker_1, worker_2, worker_3]
                
                # Execute workers in parallel
                worker_results = await asyncio.gather(
                    worker_1.execute(context),
                    worker_2.execute(context),
                    worker_3.execute(context),
                    return_exceptions=True,
                )
                
                # Collect worker steps
                for worker in self.workers:
                    self.steps.extend(worker.steps)
                
                # Synthesize results
                synthesis = {
                    "dietary_check": worker_results[0] if not isinstance(worker_results[0], Exception) else {"status": "error"},
                    "promo_optimization": worker_results[1] if not isinstance(worker_results[1], Exception) else {"status": "error"},
                    "delivery_check": worker_results[2] if not isinstance(worker_results[2], Exception) else {"status": "error"},
                }
            else:
                synthesis = {"simple_search": True}
            
            total_time = (time.time() - start_time) * 1000
            
            # Persist trajectory to database
            await self._persist_trajectory()
            
            return {
                "status": "completed",
                "session_id": self.session_id,
                "restaurants": restaurants,
                "menu_items": menu_items,
                "synthesis": synthesis,
                "execution_time_ms": total_time,
                "model_used": model_used,
                "cost_usd": llm_cost,
                "plan": plan,
                "dietary_review": dietary_review,
                "evaluation": evaluation,
                "llm_error": llm_error,
            }
            
        except Exception as e:
            logger.error(f"Lead agent execution failed: {e}")
            return {
                "status": "error",
                "session_id": self.session_id,
                "message": str(e),
            }
        finally:
            await mcp_client.disconnect()
    
    async def _persist_trajectory(self) -> None:
        """Persist agent trajectory to database."""
        try:
            async with get_session() as session:
                for step in self.steps:
                    trajectory = AgentTrajectory(
                        session_id=self.session_id,
                        user_prompt=self.user_prompt,
                        agent_type=step.agent_type,
                        worker_id=step.worker_id,
                        step_number=step.step_number,
                        tool_name=step.tool_name,
                        tool_arguments=step.tool_arguments,
                        tool_result=step.tool_result,
                        status=step.status,
                        execution_time_ms=step.execution_time_ms,
                        model_used=step.model_used,
                        cost_usd=step.cost_usd,
                    )
                    session.add(trajectory)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to persist trajectory: {e}")
