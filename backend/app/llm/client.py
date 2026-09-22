"""OpenAI-compatible client for the Smart Intern and PhD Reasoner models."""
import json
import logging
import re
from typing import Any, Optional

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Published per-million-token rates from the architecture notes. OpenRouter's
# own usage.cost wins when the provider returns it.
PRICE_PER_MILLION = {
    "meta-llama/llama-3.3-70b-instruct": 0.12,
    "anthropic/claude-sonnet-4": 3.0,
}

PLAN_SYSTEM = """You turn a dining request into a Zomato search plan. Reply with JSON only:
{"keyword":"","dietary_constraints":[],"budget_cap_inr":null,"max_delivery_mins":null,"rationale":""}
keyword is 1 to 4 food words Zomato can search, never a full sentence.
Use the caller's dietary constraints when they are provided.
Do not name restaurants or invent menu items."""

JUDGE_SYSTEM = """You judge which menu items fit the diner constraints. Reply with JSON only:
{"item_ids":[],"notes":"","allergen_flags":[]}
item_ids must be copied from the menu list. If none fit, return an empty list.
Do not invent dishes, prices, or ids."""

SCORE_SYSTEM = """You score a dining result that must stay inside the tool payload. Reply with JSON only:
{"groundedness":0,"dietary_fit":0,"safety":0,"notes":""}
Scores are 0 to 1.
groundedness is 1 only when every restaurant and item you would cite is in the payload.
dietary_fit is how well the chosen items match the stated diets.
safety is 1 only when allergen conflicts are called out instead of ignored."""


class LLMNotConfigured(RuntimeError):
    """Raised when no model API key is configured."""


def route_model(prompt: str, group_size: int = 1) -> str:
    """Send group, allergy, and multi-constraint orders to the PhD Reasoner."""
    text = prompt.lower()
    complex_query = group_size > 1 or any(
        word in text for word in ("group", "team", "people", "allergy", "allergen", "constraints")
    )
    if complex_query:
        return settings.phd_reasoner_model
    return settings.smart_intern_model


def parse_json_content(text: str) -> dict[str, Any]:
    """Read a JSON object from a model reply, including fenced output."""
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Model reply was not a JSON object")
    return parsed


def keep_known_ids(cited: list[Any], allowed: set[str]) -> list[str]:
    """Drop ids the model invented."""
    kept: list[str] = []
    for item_id in cited:
        text = str(item_id)
        if text in allowed and text not in kept:
            kept.append(text)
    return kept


def _clamp_unit(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def ground_scores(
    raw: dict[str, Any],
    *,
    cited_item_ids: list[str],
    allowed_item_ids: set[str],
) -> dict[str, Any]:
    """Cap the model's groundedness by how many cited ids actually exist."""
    known = keep_known_ids(cited_item_ids, allowed_item_ids)
    if cited_item_ids:
        id_grounding = len(known) / len(cited_item_ids)
    else:
        id_grounding = 1.0
    groundedness = min(_clamp_unit(raw.get("groundedness")), id_grounding)
    return {
        "groundedness": round(groundedness, 3),
        "dietary_fit": round(_clamp_unit(raw.get("dietary_fit")), 3),
        "safety": round(_clamp_unit(raw.get("safety")), 3),
        "notes": str(raw.get("notes") or ""),
    }


def estimate_cost(model: str, usage: dict[str, Any]) -> float:
    if usage.get("cost") not in (None, ""):
        return round(float(usage["cost"]), 6)
    tokens = float(usage.get("total_tokens") or 0)
    if not tokens:
        tokens = float(usage.get("prompt_tokens") or 0) + float(usage.get("completion_tokens") or 0)
    rate = PRICE_PER_MILLION.get(model, 0.12)
    return round(tokens / 1_000_000 * rate, 6)


class LLMClient:
    """Calls the routed model through an OpenAI-compatible chat endpoint."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = settings.llm_api_key if api_key is None else api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")

    async def complete(self, model: str, system: str, user: str) -> tuple[dict[str, Any], float]:
        if not self.api_key:
            raise LLMNotConfigured(
                "Set LLM_API_KEY to an OpenRouter or other OpenAI-compatible key. "
                f"Smart Intern is {settings.smart_intern_model}; "
                f"PhD Reasoner is {settings.phd_reasoner_model}."
            )
        payload = {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body = await self._post(payload)
        if body is None:
            payload.pop("response_format", None)
            body = await self._post(payload, required=True)
        message = body["choices"][0]["message"]["content"]
        return parse_json_content(message), estimate_cost(model, body.get("usage") or {})

    async def _post(self, payload: dict[str, Any], required: bool = False) -> Optional[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if response.status_code == 400 and "response_format" in payload and not required:
            return None
        if response.status_code >= 400:
            detail = response.text[:300]
            raise RuntimeError(f"Model API returned {response.status_code}: {detail}")
        return response.json()

    async def plan(
        self,
        query: str,
        group_size: int,
        dietary_constraints: Optional[list[str]],
        budget_cap_inr: Optional[float],
        model: str,
    ) -> tuple[dict[str, Any], float]:
        user = json.dumps(
            {
                "query": query,
                "group_size": group_size,
                "dietary_constraints": dietary_constraints or [],
                "budget_cap_inr": budget_cap_inr,
            }
        )
        parsed, cost = await self.complete(model, PLAN_SYSTEM, user)
        keyword = " ".join(str(parsed.get("keyword") or "").split())[:80]
        constraints = [str(item) for item in parsed.get("dietary_constraints") or [] if str(item).strip()]
        budget = parsed.get("budget_cap_inr")
        eta = parsed.get("max_delivery_mins")
        return {
            "keyword": keyword,
            "dietary_constraints": constraints or list(dietary_constraints or []),
            "budget_cap_inr": float(budget) if isinstance(budget, (int, float)) else budget_cap_inr,
            "max_delivery_mins": int(eta) if isinstance(eta, (int, float)) else None,
            "rationale": str(parsed.get("rationale") or ""),
            "model": model,
        }, cost

    async def judge_menu(
        self,
        query: str,
        dietary_constraints: list[str],
        menu_items: list[dict[str, Any]],
        model: str,
    ) -> tuple[dict[str, Any], float]:
        catalogue = [
            {
                "item_id": item.get("item_id"),
                "name": item.get("name"),
                "tags": item.get("tags") or [],
                "detail": item.get("detail") or "",
                "price_inr": item.get("price_inr"),
            }
            for item in menu_items[:40]
        ]
        allowed = {str(item.get("item_id")) for item in catalogue if item.get("item_id")}
        parsed, cost = await self.complete(
            model,
            JUDGE_SYSTEM,
            json.dumps({"query": query, "dietary_constraints": dietary_constraints, "menu": catalogue}),
        )
        cited = list(parsed.get("item_ids") or [])
        return {
            "item_ids": keep_known_ids(cited, allowed),
            "rejected_ids": [str(item_id) for item_id in cited if str(item_id) not in allowed],
            "notes": str(parsed.get("notes") or ""),
            "allergen_flags": [str(flag) for flag in parsed.get("allergen_flags") or []],
            "model": model,
        }, cost

    async def score(
        self,
        query: str,
        dietary_constraints: list[str],
        restaurants: list[dict[str, Any]],
        menu_items: list[dict[str, Any]],
        selected_item_ids: list[str],
        model: str,
    ) -> tuple[dict[str, Any], float]:
        payload = {
            "query": query,
            "dietary_constraints": dietary_constraints,
            "restaurants": [
                {"restaurant_id": row.get("restaurant_id"), "name": row.get("name"), "tags": row.get("tags")}
                for row in restaurants[:8]
            ],
            "menu_items": [
                {"item_id": item.get("item_id"), "name": item.get("name"), "tags": item.get("tags")}
                for item in menu_items[:40]
            ],
            "selected_item_ids": selected_item_ids,
        }
        parsed, cost = await self.complete(model, SCORE_SYSTEM, json.dumps(payload))
        allowed = {str(item.get("item_id")) for item in menu_items if item.get("item_id")}
        scores = ground_scores(parsed, cited_item_ids=selected_item_ids, allowed_item_ids=allowed)
        scores["model"] = model
        return scores, cost
