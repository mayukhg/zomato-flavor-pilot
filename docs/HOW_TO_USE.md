# How to Use FlavorPilot

**FlavorPilot** is an AI-powered autonomous dining resident that transforms natural language food requests into real Zomato orders through the Model Context Protocol (MCP). This guide walks you through installation, configuration, and daily usage.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Initial Setup](#initial-setup)
3. [Using FlavorPilot](#using-flavorpilot)
4. [Common Use Cases](#common-use-cases)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Platform-Specific Launch

| Platform | Start Command | Stop Command |
|----------|---------------|--------------|
| **macOS / Linux** | `./start.sh` | `./stop.sh` |
| **Windows (PowerShell)** | `./start.ps1` | `./stop.ps1` |

**Example:**
```bash
git clone https://github.com/mayukhg/zomato-flavor-pilot.git
cd zomato-flavor-pilot
./start.sh        # Installs dependencies on first run, then starts services
```

Once running:
- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Initial Setup

### Prerequisites

Before running FlavorPilot, ensure you have:

1. **Node.js** 18+ ([Download](https://nodejs.org/))
2. **Python** 3.12+ ([Download](https://www.python.org/))
3. **PostgreSQL** 15+ with `pgvector` extension ([Download](https://www.postgresql.org/))
4. **Git** ([Download](https://git-scm.com/))

### Environment Configuration

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```env
   # Database Configuration
   DATABASE_URL=postgresql://postgres:password@localhost:5432/flavorpilot
   
   # FastAPI Configuration
   FASTAPI_HOST=0.0.0.0
   FASTAPI_PORT=8000
   
   # MCP Server Configuration
   MCP_SERVER_TRANSPORT=stdio  # or http+sse
   MCP_SERVER_COMMAND=npx
   MCP_SERVER_ARGS=-y,@zomato/mcp-server
   MCP_SERVER_URL=http://localhost:3000/sse  # if using HTTP/SSE
   
   # Model Router Configuration
   MODEL_ROUTER_SIMPLE=meta-llama/llama-3.3-70b-instruct
   MODEL_ROUTER_COMPLEX=anthropic/claude-sonnet-4
   ```

3. **Configure PostgreSQL:**
   ```bash
   # Create database
   psql -U postgres -c "CREATE DATABASE flavorpilot;"
   
   # Enable pgvector extension
   psql -U postgres -d flavorpilot -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

### First-Time Setup

The startup script automatically handles:
- ✅ Python dependency installation
- ✅ Node.js dependency installation
- ✅ Database schema creation
- ✅ Golden dataset generation (100 test cases)
- ✅ Database seeding

Simply run:
```bash
./start.sh  # macOS/Linux
# or
./start.ps1  # Windows PowerShell
```

---

## Using FlavorPilot

### 1. Solo Mode - Personal Dining

**For individual meal planning:**

1. Navigate to http://localhost:5173
2. Ensure **Solo** mode is selected (toggle in sidebar)
3. Enter your request in natural language:

**Example Requests:**
```
"I need comfort food for a rainy evening under 500 rupees"

"Find me high-protein lunch options near Koramangala, vegan preferred"

"Something spicy and under 300 calories for dinner"

"I'm allergic to nuts - suggest safe dinner options with delivery under 30 mins"
```

4. Review the AI-generated recommendations:
   - Restaurant options with ratings
   - Menu items with nutritional info
   - Allergen warnings
   - Delivery estimates and fees

5. **Approve or modify** the staged cart
6. **Click "Approve & place Zomato order"**
7. **Review allergen verification** in the confirmation dialog
8. **Submit** to place the order

---

### 2. Group Mode - Multi-Person Orders

**For teams, families, or group dining:**

1. Toggle to **Group** mode in the sidebar
2. Enter group constraints:

**Example Group Request:**
```
"Team lunch for 6 people:
- 2 Keto diets
- 1 Vegan
- 1 severe peanut allergy
- Budget: ₹2,000 total
- Delivery within 30 minutes"
```

3. The **Lead Agent** orchestrates three **Worker Agents**:
   - **Worker 1**: Dietary & Allergen Safety
   - **Worker 2**: Price & Promo Optimization
   - **Worker 3**: Delivery & ETA Coordination

4. Review the multi-restaurant solution if needed
5. **Click "Split group bill"** to see per-person costs
6. Approve and place the order

---

### 3. Understanding the UI

#### Main Dashboard Components

**Metrics Bar** (Top):
- **Groundedness**: AI accuracy score (target: >98%)
- **Allergen Safety**: Safety verification rate (target: 100%)
- **Cost**: Average cost per query
- **Latency**: Response time

**Lead-Worker Trajectory** (Middle):
- Visual representation of agent collaboration
- Shows which worker handled which constraints
- Execution time for each step

**Restaurant Cards** (Main Area):
- Live ratings and reviews
- Delivery time estimates
- Pricing breakdown
- Dietary compatibility badges

**Staged Cart** (Right Sidebar):
- Selected items with customizations
- Macro profile (Protein, Carbs, Fat, Calories)
- Pricing breakdown (subtotal, delivery, taxes)
- Promo code application

**MCP Health Status** (Left Sidebar):
- Connection status to Zomato MCP server
- Available tools (5/5 expected)
- Last sync timestamp

---

## Common Use Cases

### Use Case 1: Quick Lunch with Dietary Restrictions

**Scenario**: You need a gluten-free lunch under ₹300 in 20 minutes.

**Steps:**
1. Switch to **Solo** mode
2. Enter: `"Gluten-free lunch under 300 rupees, fast delivery"`
3. Review suggestions filtered for gluten-free items
4. Check allergen verification (green checkmark)
5. Approve and order

**Expected Result**:
- 3-5 restaurant options
- All items marked gluten-free
- Delivery ETA < 25 minutes
- Total under ₹300 including delivery

---

### Use Case 2: Office Team Order with Budget Cap

**Scenario**: 8-person team with mixed dietary needs, ₹2,500 budget.

**Steps:**
1. Switch to **Group** mode
2. Enter detailed requirements:
   ```
   "Office lunch for 8 people, ₹2,500 budget:
   - 3 vegetarian
   - 2 non-veg
   - 1 Jain (no onion/garlic)
   - 2 prefer South Indian"
   ```
3. Wait for Lead Agent to coordinate workers (30-60 seconds)
4. Review the optimized solution
5. Click **"Split group bill"** to see ₹312.50 per person breakdown
6. Approve and order

**Expected Result**:
- Multi-restaurant recommendation if needed
- All dietary preferences satisfied
- Total under ₹2,500
- Per-person cost breakdown

---

### Use Case 3: Allergen Safety Check

**Scenario**: You have a severe shellfish allergy and need dinner.

**Steps:**
1. Enter: `"Dinner options, I have severe shellfish allergy"`
2. The **Dietary Worker Agent** flags all items with shellfish
3. Only safe options are shown
4. Before placing order, review the **Allergen Verification Panel**:
   - ✅ "No shellfish detected in selected items"
   - ✅ "Kitchen verified nut-free preparation zone"
5. Checkbox confirmation required before submission

**Expected Result**:
- Zero shellfish items in recommendations
- Clear allergen warnings on cart
- Mandatory safety acknowledgment before order

---

### Use Case 4: Optimizing with Promo Codes

**Scenario**: You want to maximize savings on a large order.

**Steps:**
1. Add items to cart (minimum ₹500 for most promos)
2. The **Price Worker Agent** automatically:
   - Scans available promo codes
   - Tests each against your cart
   - Applies the best discount
3. Cart updates with:
   - Original price: ₹850
   - Promo applied: `FLAT150`
   - Final price: ₹700

**Expected Result**:
- Best promo auto-applied
- Discount clearly shown in breakdown
- Minimum cart requirements met

---

## Advanced Features

### 1. Viewing Agent Execution Trajectories

**Purpose**: Understand how the AI made decisions.

**Access**:
1. Navigate to http://localhost:8000/api/v1/trajectory
2. Or click **"View Lead-Worker Trajectory"** in the UI

**What You See**:
```json
{
  "query": "Group lunch for 6 under ₹2,000",
  "lead_agent": {
    "decision": "complex",
    "model_used": "claude-sonnet-4",
    "reasoning": "Multi-constraint optimization required"
  },
  "workers": [
    {
      "role": "dietary",
      "findings": ["2 keto users", "1 nut allergy flagged"],
      "execution_time_ms": 1240
    },
    {
      "role": "price",
      "promo_tested": ["FLAT100", "SAVE150", "FIRSTORDER"],
      "best_promo": "SAVE150",
      "execution_time_ms": 890
    },
    {
      "role": "delivery",
      "eta_min": 28,
      "surge_detected": false,
      "execution_time_ms": 560
    }
  ]
}
```

---

### 2. Accessing the Evaluation Dashboard

**Purpose**: Monitor AI quality metrics and test results.

**Access**: http://localhost:5173 → Scroll to **"Quality is a release gate"** section

**Metrics Displayed**:
- **Groundedness Score**: 99.2% (RAG Triad evaluation)
- **Allergen Safety Rate**: 100% (no false negatives)
- **Model Routing Mix**: 85% Haiku (cheap), 15% Sonnet (complex)
- **Golden Dataset Results**: 100/100 cases passed

---

### 3. API Direct Access

**Backend API Documentation**: http://localhost:8000/docs

**Example API Calls**:

**Search Restaurants**:
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Vegan lunch under 400 rupees",
    "location": "Koramangala, Bangalore"
  }'
```

**Build Cart**:
```bash
curl -X POST http://localhost:8000/api/v1/cart/build \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "item_id": "item_123",
        "quantity": 1,
        "customizations": ["extra_spicy", "no_onion"]
      }
    ],
    "delivery_address": "123 Main St, Bangalore"
  }'
```

**Get Evaluation Results**:
```bash
curl http://localhost:8000/api/v1/evals/summary
```

---

### 4. Running Quality Tests

**Validate the AI system** using the Golden Dataset:

```bash
# Run comprehensive validation
PYTHONPATH=/workspace python3 scripts/enhanced_validation.py

# Run specific test suites
python3 scripts/test_integration.py
```

**What Gets Tested**:
- MCP client connectivity (5 tools)
- Agent orchestration (Lead + 3 Workers)
- Database schema (pgvector + SQLAlchemy)
- Allergen safety checks
- Prompt injection detection

---

## Troubleshooting

### Issue 1: Backend Not Starting

**Symptoms**: `ERR_CONNECTION_REFUSED` when accessing API

**Solution**:
```bash
# Check if backend is running
lsof -i :8000

# If not running, restart
./stop.sh && ./start.sh

# Check backend logs
tail -f backend/logs/app.log  # if logging configured
```

---

### Issue 2: Database Connection Errors

**Symptoms**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# Verify PostgreSQL is running
pg_isready -h localhost -U postgres

# If not running, start it
# macOS:
brew services start postgresql@15

# Linux:
sudo systemctl start postgresql

# Windows:
# Start PostgreSQL service from Services app

# Recreate database if needed
psql -U postgres -c "DROP DATABASE IF EXISTS flavorpilot;"
psql -U postgres -c "CREATE DATABASE flavorpilot;"
./start.sh  # Re-run setup
```

---

### Issue 3: MCP Server Connection Failed

**Symptoms**: "MCP health: 0/5 tools" in sidebar

**Solution**:

1. **Check MCP server is running**:
   ```bash
   # If using stdio transport
   npx -y @zomato/mcp-server --version
   
   # If using HTTP/SSE transport
   curl http://localhost:3000/health
   ```

2. **Verify `.env` configuration**:
   ```env
   MCP_SERVER_TRANSPORT=stdio  # or http+sse
   MCP_SERVER_URL=http://localhost:3000/sse  # if HTTP
   ```

3. **Use Mock Client for Development**:
   Edit `backend/app/config.py`:
   ```python
   USE_MOCK_MCP = True  # Set to True for offline development
   ```

---

### Issue 4: Frontend Not Loading

**Symptoms**: Blank page or "Cannot GET /" error

**Solution**:
```bash
# Check if frontend is running
lsof -i :5173

# If not running, restart
./stop.sh && ./start.sh

# Check for npm errors
cd /workspace && npm run dev

# Clear cache if needed
rm -rf node_modules/.vite
npm run dev
```

---

### Issue 5: Allergen Verification Fails

**Symptoms**: Cart approval blocked with allergen warnings

**What This Means**: The AI detected potential allergen conflicts.

**Steps**:
1. Review the **Allergen Verification Panel** in the approval dialog
2. Check which items were flagged
3. **If legitimate allergy**: Remove flagged items and re-search
4. **If false positive**: Contact support or use the feedback button

**Never bypass allergen warnings** - this is a safety-critical feature.

---

## Getting Help

### Documentation Resources

- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **Setup Guide**: `SETUP_GUIDE.md`
- **API Reference**: http://localhost:8000/docs (when running)
- **Architecture**: `docs/architecture.md`
- **Workflow**: `docs/workflow.md`

### Support Channels

- **Issues**: https://github.com/mayukhg/zomato-flavor-pilot/issues
- **Discussions**: https://github.com/mayukhg/zomato-flavor-pilot/discussions

### Feedback

FlavorPilot learns from usage. Help improve the system by:
- Reporting false allergen warnings
- Sharing successful group order patterns
- Suggesting new dietary filters
- Reporting promo code edge cases

---

**Last Updated**: September 22, 2026  
**Version**: 1.0.0  
**Maintainer**: FlavorPilot Team
