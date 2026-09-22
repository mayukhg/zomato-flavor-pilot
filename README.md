# Zomato FlavorPilot

> **Autonomous Personal Dining & Group Nutrition Resident powered by Zomato Model Context Protocol (MCP) Server.**

---

## Problem Statement

Navigating modern food delivery platforms for personal nutrition or multi-person group orders presents severe operational friction:

1. **The Multi-Constraint Group Order Trap**: Ordering for an office team or family with conflicting preferences (e.g., 2 Keto, 1 Vegan, 1 severe Peanut Allergy, ₹2,000 budget, 30-min ETA cap) requires 30+ minutes of manual restaurant search, menu comparisons, item customization checking, and promo code trial-and-error.
2. **Brittle Custom Scrapers & Unstructured LLM Tool Calls**: Traditional LLM tools rely on hardcoded web scraping or proprietary API wrappers that break whenever UI schemas change, causing hallucinated menu items, wrong pricing, or missing allergen warnings.
3. **The "Vibe-Based" Prompting & Quality Risk**: Food orders involve dietary health, religious guidelines, and severe allergies. Relying on "vibe-based" prompt testing leads to dangerous allergen hallucinations and order rejections.
4. **The "Cost Cliff" at Scale**: Defaulting to frontier LLMs for routine restaurant lookups creates an unsustainable 10x–25x cost penalty per order query.

---

## Vision

**Transforming food delivery from an intentional manual task into an autonomous, personalized, and risk-managed AI Resident service.** Zomato FlavorPilot bridges the gap between natural language dietary intent and real-time Zomato commerce execution via the Model Context Protocol (MCP).

---

## Strategy

FlavorPilot executes three strategic commitments grounded in applied AI frameworks:

1. **Standardized Context via Model Context Protocol (MCP)**: Eliminates custom API wrappers by exposing Zomato's live catalog, menu customizations, cart creation, and promo engines through a standardized MCP server protocol.
2. **Offline AI PRD & Dual Evaluation Suite**: Defines quality gates before launch using a 100-case Golden Dataset (`seed_data_flavorpilot.py`). Releases are automatically blocked if Groundedness (<98%) or Allergen Safety checks fail.
3. **Pragmatic Hybrid Model Routing**: Directs 85% of high-volume, routine menu searches to fast, fine-tuned open-weight models ("Smart Interns"), reserving frontier reasoning models ("PhDs") strictly for multi-constraint group order synthesis—saving up to 10–25x in token costs.

---

## Why MCP

### How Model Context Protocol Solves the Problem
Traditional AI integrations use ad-hoc function calling or web scrapers that fail when restaurant menus or UI components update. The **Model Context Protocol (MCP)** solves this by providing a universal, open standard for connecting AI models to Zomato's live operational backend:

- **Unified Standard**: Replaces custom integration code with standardized JSON-RPC 2.0 tool and resource declarations.
- **Dynamic Real-Time State**: Provides live access to real-time restaurant stock, dynamic pricing, surge delivery fees, and active promo codes without stale caching.
- **Strict Schema Validation**: Automatically validates item IDs, customization variant codes, and price payloads before execution, eliminating invalid cart creation calls.
- **Decoupled Security & Consent**: Runs in an isolated environment with explicit client-side consent boundaries for cart execution and payment gating.

---

## How MCP Was Implemented

Zomato FlavorPilot connects to a dedicated **Zomato MCP Server** exposing five core tools:

1. `zomato.search_restaurants`:
   - *Parameters*: `query` (string), `location` (string), `cuisine` (string), `max_delivery_mins` (integer), `budget_cap_inr` (number).
   - *Returns*: List of active restaurants with live ratings, delivery fees, and estimated preparation times.
2. `zomato.get_menu`:
   - *Parameters*: `restaurant_id` (string), `dietary_filter` (`vegan` | `keto` | `halal` | `nut_free`).
   - *Returns*: Categorized menu items with full ingredient lists and allergen tags.
3. `zomato.get_item_customizations`:
   - *Parameters*: `item_id` (string).
   - *Returns*: Mandatory and optional variant groups (portion size, spice level, add-ons).
4. `zomato.apply_promo_code`:
   - *Parameters*: `cart_id` (string), `promo_code` (string).
   - *Returns*: Updated order total, discount applied, and minimum cart value requirements.
5. `zomato.build_cart`:
   - *Parameters*: `items` (array of item objects with customization IDs), `delivery_address` (object).
   - *Returns*: Staged cart token ready for user approval and payment execution.

---

## Why and How AI

### Why AI is Used
Traditional algorithmic search engines cannot interpret nuanced human desires like *"comfort food for a rainy evening that fits my 1,800-calorie daily goal and doesn't trigger my gluten intolerance."* AI provides the multi-step reasoning required to balance dietary health, taste preferences, group constraints, and cost optimization simultaneously.

### How AI is Implemented
FlavorPilot calls a live model on every search, then uses Zomato MCP for restaurants and menus. The client is `backend/app/llm/client.py`. It speaks the OpenAI chat-completions API. OpenRouter is the default host because it serves both model ids.

Routing (`route_model`):

- **Smart Intern** (`meta-llama/llama-3.3-70b-instruct`) handles a solo request with no group or allergy language.
- **PhD Reasoner** (`anthropic/claude-sonnet-4`) handles `group_size` greater than 1, or a prompt that mentions group, team, people, allergy, allergen, or constraints.

Each search makes three model calls with that routed model:

1. **Plan.** Turn the prompt into a short Zomato keyword, dietary constraints, budget, ETA, and a rationale. The keyword is what `get_restaurants_for_keyword` searches. The model is told not to name restaurants.
2. **Judge.** After the live menu is loaded, keep only `item_id`s that appear on that menu. Unknown ids are dropped. Notes and allergen flags come back with the kept ids.
3. **Score.** Return groundedness, dietary fit, and safety from 0 to 1. Groundedness is capped by how many cited item ids actually exist, so a model cannot claim a perfect score for invented dishes.

The same score call is available on its own as `POST /api/v1/evals/judge`. It does not read the database and does not place an order.

If `LLM_API_KEY` is empty, Zomato search still runs. The UI shows **Reasoner did not run** and the metrics stay blank. Set the key and restart the API. The process reads `.env` only at startup.

```env
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
SMART_INTERN_MODEL=meta-llama/llama-3.3-70b-instruct
PHD_REASONER_MODEL=anthropic/claude-sonnet-4
```

Cost uses the provider `usage.cost` when OpenRouter sends it. Otherwise the client estimates from token counts at $0.12 per million for the Smart Intern and $3.00 per million for the PhD Reasoner. The header shows that cost and the latency of the last search.

---

## Roadmap

| Phase | Scope | Status |
| :--- | :--- | :--- |
| **Phase 0 — System Design & Specs** | Architecture specs, 8-block system prompt, Zomato MCP schema definition, and 100-case Golden Dataset generator (`seed_data_flavorpilot.py`). | ✅ Done |
| **Phase 1 — Pilot Prototype (Zomato FlavorPilot)** | Interactive Lovable React SPA UI, FastAPI backend server scaffold, PostgreSQL + pgvector schema, and Lead-Worker agent loop. | ✅ Done (Pilot) |
| **Phase 2 — Multi-Restaurant Group Split & MCP Enclave** | Advanced multi-restaurant group order splitting, automated bill calculation, and local open-weight model deployment. | 🔄 In Progress |
| **Phase 3 — Real-Time Order Drift Shield** | Live traffic sampling (1–10%), real-time Groundedness & P95/P99 latency monitoring, and automated capture of cart rejections. | ⏳ Scheduled |
| **Phase 4 — Future Expansion** | **Zomato Grocery/Instamart Resident**: Automated weekly pantry replenishment.<br>**Group Dining Concierge**: Table booking and pre-ordered dining experiences. | 📅 Future Roadmap |

---

## Quick Start

### 📡 Connecting to Zomato MCP Server

FlavorPilot supports **two integration approaches** with the official Zomato MCP server:

#### **Option 1: Native Cursor MCP (Recommended for IDE Users) ⭐**

Connect Cursor IDE directly to Zomato MCP - **no Python setup required**:

1. **Add to Cursor's `mcp.json`:**
   ```json
   {
     "mcpServers": {
       "zomato-mcp-server": {
         "url": "https://mcp-server.zomato.com/mcp",
         "transport": {
           "type": "sse"
         }
       }
     }
   }
   ```

2. **Restart Cursor** - Zomato tools will appear in MCP tool picker

**See:** [`docs/CURSOR_MCP_INTEGRATION.md`](docs/CURSOR_MCP_INTEGRATION.md) for complete guide

#### **Option 2: Python Backend Integration**

For FlavorPilot backend and autonomous agents:

```bash
# In .env
USE_MOCK_MCP=false
ZOMATO_MCP_TRANSPORT=stdio
ZOMATO_MCP_SERVER_URL=https://mcp-server.zomato.com/mcp
ZOMATO_MCP_STDIO_CMD=npx -y mcp-remote https://mcp-server.zomato.com/mcp
ZOMATO_ADDRESS_ID=217570301
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-openrouter-key
```

Restart the API after changing `LLM_API_KEY`. Search still returns Zomato kitchens without it, and the UI reports that the reasoner did not run.

**Test connection:**
```bash
python3 scripts/test_zomato_mcp_connection.py
```

**See:** [`docs/ZOMATO_MCP_SETUP.md`](docs/ZOMATO_MCP_SETUP.md) for backend setup

---

### 🚀 Platform-Specific Commands & Installation

### Prerequisites
- [Node.js](https://nodejs.org/) 18+ & [Bun](https://bun.sh/)
- [Python](https://www.python.org/) 3.12+
- [PostgreSQL](https://www.postgresql.org/) with `pgvector` extension
- Active Zomato MCP Server instance or local mock MCP runner

### Quick start (recommended):

| Platform | Start | Stop |
| --- | --- | --- |
| macOS / Linux | `./start.sh` | `./stop.sh` |
| Windows (PowerShell) | `./start.ps1` | `./stop.ps1` |

**Example:**
```bash
git clone https://github.com/mayukhg/zomato-flavor-pilot.git
cd zomato-flavor-pilot
./start.sh        # installs dependencies on first run, then starts the API and cockpit
```

### Manual Setup & Run

```bash
# Clone repository
git clone https://github.com/mayukhg/zomato-flavor-pilot.git
cd zomato-flavor-pilot

# Install frontend and backend dependencies
npm install
pip install -r backend/requirements.txt

# Seed Golden Dataset & Database
python seed_data_flavorpilot.py
python scripts/seed_database.py

# Launch local dev environment (Lovable UI + FastAPI + MCP Bridge)
./start.sh
```
