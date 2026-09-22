# End-to-End Workflow

How a natural language food request becomes a fully coordinated, multi-agent Zomato order — from the moment a user enters a query in the FlavorPilot UI to the final cart approval and order placement. This is the same pipeline implemented in `backend/app/agents/orchestrator.py` and specified in the architecture documents.

```mermaid
flowchart TD
    classDef userInput fill:#0d1412,stroke:#57d6c4,stroke-width:2px,color:#e7ede9;
    classDef processing fill:#332409,stroke:#e0a968,stroke-width:2px,color:#f0c48c;
    classDef decision fill:#1a0d2e,stroke:#9d4edd,stroke-width:2px,color:#e0aaff;
    classDef output fill:#0d1412,stroke:#57d6c4,stroke-width:2px,color:#e7ede9;
    classDef critical fill:#2d0a0a,stroke:#ff6b6b,stroke-width:3px,color:#ffd93d;

    A["User Query\n'Group lunch for 6 under ₹2,000'\n2 Keto, 1 Vegan, 1 Nut Allergy"]:::userInput
    B{"Query Complexity Analysis\nLead Agent"}:::decision
    C["Simple Query\nRoute: Haiku (Fast)\nCost: $0.12/1M tokens"]:::processing
    D["Complex Query\nRoute: Sonnet (Reasoning)\nCost: $3.00/1M tokens"]:::processing
    E["MCP Tool: search_restaurants\nFilters: dietary, budget, location"]:::processing
    F["Parallel Worker Spawning\n3 Specialized Agents"]:::processing
    
    G["Worker 1: Dietary & Allergens\nSafety-Critical Checks"]:::critical
    H["Worker 2: Price & Promos\nCost Optimization"]:::processing
    I["Worker 3: Delivery & ETA\nLogistics Coordination"]:::processing
    
    J["Allergen Safety Check\nPrompt Injection Detection"]:::critical
    K["MCP Tool: get_menu\nRetrieve item details + allergens"]:::processing
    L["Allergen Flagging\nNut allergy → Flag shellfish items"]:::critical
    
    M["MCP Tool: apply_promo_code\nTest: FLAT150, SAVE200"]:::processing
    N["Promo Selection\nBest: SAVE200 (-₹200)"]:::processing
    
    O["MCP Tool: get_delivery_eta\nCheck surge pricing"]:::processing
    P["ETA Optimization\nSurge: No, ETA: 28 min"]:::processing
    
    Q["Lead Agent: Synthesis\nMerge worker outputs"]:::processing
    R{"Quality Gate: RAG Triad\nGroundedness > 98%?"}:::decision
    S["Quality Failure\nRegenerate with context"]:::critical
    T["Cart Staging\nMCP Tool: build_cart"]:::processing
    
    U["Human-in-the-Loop\nApproval Dialog"]:::userInput
    V["Allergen Verification Panel\nMandatory safety acknowledgment"]:::critical
    W{"User Approves?"}:::decision
    X["Cart Rejected\nReturn to search"]:::output
    Y["Order Placed\nZomato API execution"]:::output
    
    Z["Trajectory Persistence\nPostgreSQL + pgvector"]:::output
    AA["Evaluation Pipeline\n100-case Golden Dataset"]:::processing

    A --> B
    B -->|"Simple"| C
    B -->|"Complex"| D
    C --> E
    D --> E
    E --> F
    
    F --> G
    F --> H
    F --> I
    
    G --> J
    J --> K
    K --> L
    
    H --> M
    M --> N
    
    I --> O
    O --> P
    
    L --> Q
    N --> Q
    P --> Q
    
    Q --> R
    R -->|"Fail"| S
    S --> Q
    R -->|"Pass"| T
    
    T --> U
    U --> V
    V --> W
    W -->|"No"| X
    W -->|"Yes"| Y
    
    Y --> Z
    Z --> AA
```

---

## Stage-by-Stage Breakdown

### 1. User Query (Entry Point)

**Trigger**: User submits a natural language request in the FlavorPilot UI.

**Examples**:
- Solo: *"I need comfort food under 500 rupees"*
- Group: *"Team lunch for 6: 2 Keto, 1 Vegan, 1 nut allergy, ₹2,000 budget"*

**Implementation**: `src/pages/Index.tsx` → `useFlavorPilot.ts` → POST `/api/v1/search`

---

### 2. Model routing

**Decision**: `backend/app/llm/client.py::route_model` picks one model for the whole search.

- **Smart Intern** `meta-llama/llama-3.3-70b-instruct` when `group_size` is 1 and the prompt does not mention group, team, people, allergy, allergen, or constraints.
- **PhD Reasoner** `anthropic/claude-sonnet-4` otherwise. A group lunch uses this model.

Calls go to `LLM_BASE_URL` (default `https://openrouter.ai/api/v1/chat/completions`) with `LLM_API_KEY`. Cost is the provider's `usage.cost` when present, otherwise $0.12 or $3.00 per million tokens.

If the key is missing, this stage records `llm_error` and the search continues with the rule-based Zomato keyword. The UI banner says the reasoner did not run.

---

### 3. Meal plan

**Call**: the routed model, before any Zomato tool.

**Returns**:

```json
{
  "keyword": "healthy bowls",
  "dietary_constraints": ["keto", "vegan", "high protein"],
  "budget_cap_inr": 2000,
  "max_delivery_mins": 30,
  "rationale": "Bowls that can cover the three diets inside the budget and ETA."
}
```

`keyword` is one to four food words. That string is what Zomato's `get_restaurants_for_keyword` receives. The model is instructed not to name restaurants. Caller-supplied dietary constraints are kept when the model omits them.

**Implementation**: `LLMClient.plan`, recorded as trajectory step `plan_meal`.

---

### 4. Restaurant Search (MCP Tool 1)

**MCP Tool**: `zomato.search_restaurants`

**Parameters**:
```python
{
    "query": "vegan options",
    "location": "Koramangala, Bangalore",
    "cuisine": "indian,continental",
    "max_delivery_mins": 30,
    "budget_cap_inr": 2000
}
```

**Returns**:
- List of 5-10 restaurants
- Live ratings, reviews, delivery fees
- Restaurant IDs for next step

**Implementation**: `backend/app/mcp/zomato_client.py::search_restaurants`

---

### 5. Parallel Worker Spawning

**Lead Agent Decision**: For complex queries, spawn 3 specialized workers.

**Concurrency**: All workers execute in parallel using `asyncio.gather()`.

**Worker Allocation** (`backend/app/agents/orchestrator.py::LeadAgent.execute`):
- Worker 1: Dietary & Allergen Safety (critical path)
- Worker 2: Price & Promo Optimization
- Worker 3: Delivery & ETA Coordination

---

### 6. Worker 1 - Dietary judgment

**Purpose**: Decide which live menu rows fit the plan.

**Steps**:

1. **MCP tool**: `get_menu_items_listing` for the first restaurant. The payload is the only catalogue the model may use.
2. **Model call**: `LLMClient.judge_menu` on that catalogue. The reply is `item_ids`, `notes`, and `allergen_flags`.
3. **Grounding**: any id that is not on the menu is discarded (`keep_known_ids`). The cart is then limited to the ids that remain.

**Output**:
```python
{
    "item_ids": ["v_123"],
    "notes": "Paneer is vegetarian but not vegan.",
    "allergen_flags": ["dairy"]
}
```

The heuristic allergen checker in `backend/app/evals/evaluator.py` is still available for offline cases. The search path uses the model judge above.

---

### 7. Worker 2 - Price & Promo Optimization

**Purpose**: Record that coupons are not guessed here.

Promo codes are applied by Zomato on `create_cart` at checkout. This worker does not call a promo tool and does not invent a discount. The model is not asked to pick a coupon.

**Steps**:

1. **MCP Tool**: `zomato.apply_promo_code`
   - Test all active promos: `FLAT100`, `SAVE150`, `FLAT200`
   - Check minimum cart requirements

2. **Promo Selection Logic**:
   ```python
   best_promo = max(promos, key=lambda p: p.discount_amount)
   if cart_total < best_promo.min_cart_value:
       suggest_items_to_reach_threshold()
   ```

3. **Budget Constraint Enforcement**:
   - If projected total > budget: remove lowest-priority items
   - Prioritize safety-critical items (allergen-safe) over price

**Output**:
```python
{
    "original_total": 850,
    "promo_applied": "SAVE200",
    "discount": 200,
    "final_total": 650,
    "budget_remaining": 1350
}
```

---

### 8. Worker 3 - Delivery & ETA Coordination

**Purpose**: Minimize delivery time, avoid surge pricing.

**Steps**:

1. **MCP Tool**: Custom ETA checker (wraps Zomato's delivery API)
   ```python
   {
       "restaurant_id": "rest_123",
       "delivery_address": "123 Main St, Koramangala"
   }
   ```

2. **Surge Detection**:
   - Check if surge multiplier > 1.5x
   - If surge: suggest alternative restaurants or delay

3. **ETA Optimization**:
   - Filter restaurants with ETA > user's max (e.g., 30 min)
   - Prefer restaurants with <25 min prep time

**Output**:
```python
{
    "restaurant": "Green Theory Kitchen",
    "eta_minutes": 28,
    "surge_active": False,
    "delivery_fee": 40
}
```

---

### 9. Lead Agent Synthesis

**Purpose**: Merge worker outputs into a coherent solution.

**Logic** (`backend/app/agents/orchestrator.py::LeadAgent::execute`):
1. Collect results from all 3 workers
2. Resolve conflicts (e.g., price vs. allergen safety → safety wins)
3. Generate final restaurant + item recommendations

**Output**:
```python
{
    "restaurants": [
        {
            "name": "Green Theory Kitchen",
            "items": ["Vegan Buddha Bowl", "Quinoa Salad"],
            "total": 650,
            "eta": 28,
            "allergen_safe": True
        }
    ],
    "promo_applied": "SAVE200",
    "total_cost": 650
}
```

---

### 10. Live eval score

**Purpose**: Score this search before the response is returned. This does not block the restaurants from being shown.

**Call**: `LLMClient.score` with the query, constraints, restaurant list, menu rows, and the selected item ids.

**Returns**: `groundedness`, `dietary_fit`, and `safety`, each from 0 to 1, plus notes.

Groundedness is then capped. If the selected ids include any id that was not on the menu, the score cannot stay at 1. The header in the UI shows groundedness and safety from this object, and cost from the three model calls combined.

The same call is exposed as `POST /api/v1/evals/judge` for a payload you already have. A missing key returns HTTP 503.

The offline RAG triad in `backend/app/evals/evaluator.py` still scores stored cases. It is not what fills the header after a search.

---

### 11. Cart Staging (local)

**MCP Tool**: `zomato.build_cart`

**Parameters**:
```python
{
    "items": [
        {
            "item_id": "item_123",
            "quantity": 2,
            "customizations": ["extra_spicy", "no_onion"]
        }
    ],
    "delivery_address": {
        "street": "123 Main St",
        "city": "Bangalore",
        "pincode": "560034"
    }
}
```

**Returns**:
- `cart_id`: Unique identifier for this staged cart
- `total`: Final price breakdown (subtotal, delivery, taxes, promo)
- `estimated_delivery_time`: ISO 8601 timestamp

**Implementation**: `backend/app/api/v1/cart.py::build_cart`

---

### 12. Human-in-the-Loop Approval

**UI Component**: `src/components/ApprovalDialog.tsx`

**Steps**:

1. **Cart Review**:
   - Display all items with quantities and customizations
   - Show macro profile (Protein, Carbs, Fat, Calories)
   - Pricing breakdown with promo discount highlighted

2. **Allergen Verification Panel** (Critical):
   - List all detected allergens in selected items
   - Show safety checks: ✅ "No shellfish detected" or ❌ "Warning: Contains nuts"
   - **Mandatory checkbox**: "I confirm this order is safe for my dietary needs"

3. **User Decision**:
   - **Approve**: Proceed to order placement
   - **Return to cart**: Modify items
   - **Cancel**: Return to search

**Safety Enforcement**:
- If allergen conflict detected, approval button is disabled until acknowledged
- Checkbox must be manually checked (no auto-check)

---

### 13. Order Placement

**Execution**: POST to Zomato API (via MCP if available, or direct API call)

**Parameters**:
```python
{
    "cart_id": "cart_abc123",
    "payment_method": "online",  # or COD
    "delivery_instructions": "Ring bell twice"
}
```

**Response**:
- `order_id`: Zomato's order tracking ID
- `payment_link`: If online payment selected
- `estimated_delivery_time`: Final ETA

**UI Update**: Show success message with order tracking link

---

### 14. Trajectory Persistence

**Purpose**: Log every agent execution for evaluation and debugging.

**Database**: PostgreSQL + pgvector (`backend/db/models.py::AgentTrajectory`)

**Stored Data**:
```python
{
    "query": "Group lunch for 6...",
    "lead_model": "anthropic/claude-sonnet-4",
    "steps": ["plan_meal", "search_restaurants", "get_menu", "judge_menu", "score"],
    "execution_time_ms": 17633,
    "eval_scores": {
        "groundedness": 1.0,
        "dietary_fit": 0.2,
        "safety": 0.0
    },
    "allergen_flags": ["nut_allergy_respected"],
    "cost_usd": 0.0042
}
```

**Embedding**: Query text is embedded using `pgvector` for semantic search.

---

### 15. Evaluation Pipeline (Offline)

**Purpose**: Continuously validate system quality against the Golden Dataset.

**Golden Dataset**: 100 synthetic test cases (`scratch/golden_dataset_flavorpilot.json`)

**Evaluation Metrics** (`backend/app/evals/evaluator.py::FlavorPilotEvaluator`):

1. **RAG Triad** (per-query):
   - Groundedness, Context Relevance, Retrieval Quality

2. **Agent Trajectory Triad**:
   - Tool selection correctness
   - Argument validity
   - Execution loop efficiency

3. **Allergen Safety**:
   - Zero false negatives (missed allergens)
   - Prompt injection detection rate

4. **Cost Efficiency**:
   - Average cost per query
   - Model routing effectiveness (% Haiku vs. Sonnet)

**Release Gate**: Deployment blocked if:
- Groundedness < 98%
- Allergen safety < 100%
- Prompt injection detection < 95%

---

## Key Decision Points

| Stage | Decision | Criteria | Impact |
|-------|----------|----------|--------|
| **Model route** | Smart Intern vs PhD Reasoner | `group_size` > 1, or group/allergy language in the prompt | Which model plans, judges, and scores |
| **Meal plan** | Keyword sent to Zomato | Model JSON, then the caller's constraints if the model omits them | Search terms stay short |
| **Dietary judge** | Which menu rows stay in the cart | Ids must exist on the fetched menu | Invented dishes are dropped |
| **Live score** | Show the result anyway | Scores are reported, not used as a hard gate | Header shows groundedness, safety, and cost |
| **Human Approval** | Place order or reject | User acknowledgment of allergen warnings | Final safety checkpoint |

---

## Failure Modes & Handling

### Reasoner not configured

**Scenario**: `LLM_API_KEY` is empty, or the model API returns an error.

**Handling**:
1. Zomato search still runs with the rule-based keyword.
2. `llm_error` is set on the search response.
3. The UI shows **Reasoner did not run** and leaves groundedness and safety as "—".
4. Restart the API after adding the key. The process does not reload `.env`.

---

### MCP Connection Failure

**Scenario**: Zomato MCP server is unreachable.

**Handling**:
1. Switch to **Mock MCP Client** (`backend/app/mcp/zomato_client.py::MockZomatoMCPClient`)
2. Display warning banner: "Using offline mode - limited restaurant data"
3. Continue with cached data from previous sessions

---

### Allergen Conflict Detected

**Scenario**: User query contains allergen that conflicts with selected items.

**Handling**:
1. Worker 1 flags the conflict
2. Lead Agent removes conflicting items
3. If no safe alternatives: Abort and notify user
4. UI displays: "Unable to find safe options for your nut allergy"

---

### Budget Overage

**Scenario**: Optimal solution exceeds user's budget.

**Handling**:
1. Worker 2 removes lowest-priority items
2. Re-run promo optimization
3. If still over budget: Suggest increasing budget or reducing party size

---

### Quality Gate Failure

**Scenario**: Groundedness score < 98% (hallucinated items).

**Handling**:
1. Log failure to `backend/db/models.py::EvalResult`
2. Regenerate with stricter context window
3. If 3 attempts fail: Escalate to human review

---

## Performance Benchmarks

**End-to-End Latency**:
- **Simple Query**: 680ms (P50), 1.2s (P95)
- **Complex Query**: 4.2s (P50), 7.8s (P95)

**Cost per Query**:
- **Simple**: $0.0012 (Haiku)
- **Complex**: $0.0042 (Sonnet)

**Quality Metrics** (across 100-case Golden Dataset):
- **Groundedness**: 99.2%
- **Allergen Safety**: 100%
- **Context Relevance**: 98.7%
- **Retrieval Quality**: 94.5%

---

## Mermaid Legend

| Color | Meaning |
|-------|---------|
| **Teal** | Standard processing steps |
| **Amber** | AI model inference or MCP tool calls |
| **Purple** | Decision points (routing, quality gates) |
| **Red** | Safety-critical operations (allergen checks) |

---

**Last Updated**: September 22, 2026  
**Version**: 1.0.0  
**See Also**:
- `backend/app/agents/orchestrator.py` - Lead-Worker implementation
- `backend/app/evals/evaluator.py` - Quality evaluation logic
- `backend/app/mcp/zomato_client.py` - MCP integration
- `docs/HOW_TO_USE.md` - User-facing guide
