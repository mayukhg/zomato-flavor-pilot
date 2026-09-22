# Development Guide

Complete guide for setting up a development environment and contributing to FlavorPilot.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Code Style](#code-style)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)

---

## Development Setup

### Prerequisites Installation

#### 1. **Python 3.12+**

**macOS (Homebrew)**:
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

**Windows**:
- Download from [python.org](https://www.python.org/downloads/)
- Check "Add Python to PATH" during installation

---

#### 2. **Node.js 18+**

**macOS (Homebrew)**:
```bash
brew install node@18
```

**Linux (NVM)**:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

**Windows**:
- Download from [nodejs.org](https://nodejs.org/)

---

#### 3. **PostgreSQL 15+ with pgvector**

**macOS (Homebrew)**:
```bash
brew install postgresql@15
brew services start postgresql@15

# Install pgvector
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt install postgresql-15 postgresql-contrib-15
sudo systemctl start postgresql

# Install pgvector
sudo apt install postgresql-server-dev-15
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**Windows**:
- Download PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/)
- Compile pgvector from source or use Docker

---

#### 4. **Git**

**macOS**:
```bash
brew install git
```

**Linux**:
```bash
sudo apt install git
```

**Windows**:
- Download from [git-scm.com](https://git-scm.com/)

---

### Repository Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/mayukhg/zomato-flavor-pilot.git
   cd zomato-flavor-pilot
   ```

2. **Create Python virtual environment**:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or
   .\venv\Scripts\activate  # Windows PowerShell
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

5. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

6. **Setup database**:
   ```bash
   # Create database
   createdb flavorpilot
   
   # Or using psql
   psql -U postgres -c "CREATE DATABASE flavorpilot;"
   
   # Enable pgvector
   psql -U postgres -d flavorpilot -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

7. **Generate Golden Dataset**:
   ```bash
   python seed_data_flavorpilot.py
   ```

8. **Seed database**:
   ```bash
   python scripts/seed_database.py
   ```

---

## Project Structure

```
zomato-flavor-pilot/
├── backend/                    # Python backend
│   ├── app/
│   │   ├── agents/            # Lead-Worker agents
│   │   │   └── orchestrator.py
│   │   ├── api/               # FastAPI routes
│   │   │   └── v1/
│   │   │       ├── search.py
│   │   │       ├── cart.py
│   │   │       ├── trajectory.py
│   │   │       └── evals.py
│   │   ├── evals/             # Evaluation framework
│   │   │   └── evaluator.py
│   │   ├── mcp/               # MCP integration
│   │   │   └── zomato_client.py
│   │   ├── config.py          # Pydantic settings
│   │   ├── main.py            # FastAPI entry point
│   │   └── schemas.py         # API models
│   ├── db/                    # Database layer
│   │   ├── connection.py      # SQLAlchemy engine
│   │   └── models.py          # ORM models + pgvector
│   └── requirements.txt       # Python dependencies
│
├── src/                       # React frontend
│   ├── components/            # UI components
│   │   ├── HeroSection.tsx
│   │   ├── MetricsBar.tsx
│   │   ├── RestaurantCard.tsx
│   │   ├── StagedCart.tsx
│   │   ├── ApprovalDialog.tsx
│   │   └── SplitBillDialog.tsx
│   ├── hooks/
│   │   └── useFlavorPilot.ts  # API integration
│   ├── pages/
│   │   └── Index.tsx          # Main page
│   ├── services/
│   │   └── api.ts             # Axios + TanStack Query
│   └── lib/
│       └── utils.ts
│
├── scripts/                   # Automation scripts
│   ├── seed_data_flavorpilot.py
│   ├── seed_database.py
│   ├── enhanced_validation.py
│   ├── capture_ui_screenshots.js
│   └── validate_scripts.sh
│
├── docs/                      # Documentation
│   ├── HOW_TO_USE.md
│   ├── workflow.md
│   ├── architecture.md
│   └── development.md
│
├── screenshots/               # UI test screenshots
├── scratch/                   # Generated data
│   └── golden_dataset_flavorpilot.json
│
├── start.sh / start.ps1       # Startup scripts
├── stop.sh / stop.ps1         # Shutdown scripts
├── .env.example               # Environment template
├── package.json               # Node.js config
├── tsconfig.json              # TypeScript config
└── vite.config.ts             # Vite config
```

---

## Development Workflow

### Running the Development Server

**Option 1: Automated (Recommended)**
```bash
./start.sh  # macOS/Linux
# or
./start.ps1  # Windows PowerShell
```

**Option 2: Manual**

**Terminal 1 - Backend**:
```bash
cd backend
source ../venv/bin/activate  # if not already activated
python -m app.main
```

**Terminal 2 - Frontend**:
```bash
npm run dev
```

**Access**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

### Making Changes

#### Backend Changes

1. **Edit Python files** in `backend/app/`
2. **FastAPI auto-reloads** on save (development mode)
3. **Test changes** via http://localhost:8000/docs

**Example: Add a new API endpoint**

```python
# backend/app/api/v1/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

**Register router**:
```python
# backend/app/api/v1/__init__.py
from .health import router as health_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router, tags=["health"])
```

---

#### Frontend Changes

1. **Edit TypeScript/React files** in `src/`
2. **Vite hot-reloads** automatically
3. **Browser refreshes** instantly

**Example: Add a new component**

```typescript
// src/components/CustomComponent.tsx
import { useState } from 'react';

export const CustomComponent = () => {
  const [count, setCount] = useState(0);
  
  return (
    <div className="p-4 border rounded">
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
};
```

**Use in page**:
```typescript
// src/pages/Index.tsx
import { CustomComponent } from '@/components/CustomComponent';

export default function Index() {
  return (
    <div>
      <CustomComponent />
    </div>
  );
}
```

---

#### Database Schema Changes

1. **Edit models** in `backend/db/models.py`
2. **Create migration** (if using Alembic):
   ```bash
   alembic revision --autogenerate -m "Add new field"
   alembic upgrade head
   ```
3. **Or manually update** schema:
   ```bash
   psql -d flavorpilot -f migrations/0002_add_field.sql
   ```

---

### Git Workflow

**Branch Naming**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring

**Example Workflow**:
```bash
# Create feature branch
git checkout -b feature/add-promo-optimizer

# Make changes
# ... edit files ...

# Stage and commit
git add .
git commit -m "feat: Add promo code optimization logic"

# Push to remote
git push -u origin feature/add-promo-optimizer

# Create Pull Request on GitHub
```

---

## Testing

### Backend Tests

**Run all tests**:
```bash
cd backend
pytest
```

**Run specific test file**:
```bash
pytest tests/test_agents.py
```

**Run with coverage**:
```bash
pytest --cov=app --cov-report=html
```

**Example Test**:
```python
# backend/tests/test_agents.py
import pytest
from app.agents.orchestrator import LeadAgent

@pytest.mark.asyncio
async def test_lead_agent_simple_query():
    agent = LeadAgent()
    result = await agent.execute("Find vegan lunch under 400 rupees")
    
    assert result is not None
    assert len(result["restaurants"]) > 0
    assert result["total_cost"] <= 400
```

---

### Frontend Tests

**Run tests**:
```bash
npm test
```

**Example Test**:
```typescript
// src/components/__tests__/CustomComponent.test.tsx
import { render, fireEvent } from '@testing-library/react';
import { CustomComponent } from '../CustomComponent';

describe('CustomComponent', () => {
  it('increments count on button click', () => {
    const { getByText } = render(<CustomComponent />);
    const button = getByText('Increment');
    
    fireEvent.click(button);
    
    expect(getByText('Count: 1')).toBeInTheDocument();
  });
});
```

---

### Integration Tests

**Validation Suite**:
```bash
PYTHONPATH=/workspace python3 scripts/enhanced_validation.py
```

**Tests**:
- MCP client connectivity (5 tools)
- Agent orchestration (Lead + 3 Workers)
- Database schema (pgvector)
- Allergen safety checks

---

### UI Screenshot Tests

**Generate screenshots**:
```bash
npm run dev  # Start frontend first
node scripts/capture_ui_screenshots.js
```

**Output**: `screenshots/*.png` (15 test cases)

---

## Code Style

### Python (Backend)

**Style Guide**: PEP 8

**Linting**:
```bash
# Install tools
pip install black isort flake8 mypy

# Format code
black backend/
isort backend/

# Check style
flake8 backend/
mypy backend/
```

**Example**:
```python
# Good
async def search_restaurants(
    query: str,
    location: str,
    budget_cap: float
) -> list[Restaurant]:
    """Search for restaurants matching criteria.
    
    Args:
        query: Search query string
        location: Location for search
        budget_cap: Maximum budget in INR
        
    Returns:
        List of matching restaurants
    """
    results = await mcp_client.search_restaurants(
        query=query,
        location=location,
        budget_cap_inr=budget_cap
    )
    return results
```

---

### TypeScript (Frontend)

**Style Guide**: Airbnb + Prettier

**Linting**:
```bash
npm run lint
npm run format
```

**Example**:
```typescript
// Good
interface RestaurantCardProps {
  name: string;
  rating: number;
  deliveryTime: number;
  onSelect: () => void;
}

export const RestaurantCard: React.FC<RestaurantCardProps> = ({
  name,
  rating,
  deliveryTime,
  onSelect,
}) => {
  return (
    <div className="border rounded p-4 hover:shadow-lg">
      <h3 className="text-lg font-bold">{name}</h3>
      <p>Rating: {rating}/5</p>
      <p>Delivery: {deliveryTime} min</p>
      <button onClick={onSelect}>Select</button>
    </div>
  );
};
```

---

## Common Tasks

### Task 1: Add a New MCP Tool

**1. Define tool in MCP client**:
```python
# backend/app/mcp/zomato_client.py
async def get_restaurant_reviews(self, restaurant_id: str) -> dict:
    """Fetch reviews for a restaurant."""
    return await self._call_tool(
        "zomato.get_restaurant_reviews",
        {"restaurant_id": restaurant_id}
    )
```

**2. Add schema**:
```python
# backend/app/schemas.py
class ReviewResponse(BaseModel):
    restaurant_id: str
    reviews: list[dict]
    average_rating: float
```

**3. Create API endpoint**:
```python
# backend/app/api/v1/reviews.py
@router.get("/reviews/{restaurant_id}")
async def get_reviews(restaurant_id: str) -> ReviewResponse:
    reviews = await mcp_client.get_restaurant_reviews(restaurant_id)
    return ReviewResponse(**reviews)
```

---

### Task 2: Add a New Worker Agent

**1. Define worker class**:
```python
# backend/app/agents/orchestrator.py
class ReviewAnalysisWorker(WorkerAgent):
    role = "review_analysis"
    
    async def execute(self, context: dict) -> dict:
        restaurant_id = context["restaurant_id"]
        reviews = await self.mcp_client.get_restaurant_reviews(restaurant_id)
        
        # Analyze sentiment
        positive_reviews = [r for r in reviews if r["rating"] >= 4]
        
        return {
            "sentiment": "positive" if len(positive_reviews) > len(reviews) / 2 else "negative",
            "review_count": len(reviews)
        }
```

**2. Spawn from Lead Agent**:
```python
# backend/app/agents/orchestrator.py (LeadAgent.execute)
if self._determine_complexity(query) == "complex":
    workers = [
        DietaryWorker(...),
        PriceWorker(...),
        DeliveryWorker(...),
        ReviewAnalysisWorker(...)  # New worker
    ]
    results = await asyncio.gather(*[w.execute(context) for w in workers])
```

---

### Task 3: Add a New Evaluation Metric

**1. Define metric calculator**:
```python
# backend/app/evals/evaluator.py
class ResponseTimeEvaluator:
    def evaluate(self, trajectory: AgentTrajectory) -> float:
        """Calculate response time score (0-1)."""
        execution_time_ms = trajectory.execution_time_ms
        
        # Target: < 5 seconds for complex queries
        if execution_time_ms < 5000:
            return 1.0
        elif execution_time_ms < 10000:
            return 0.8
        else:
            return 0.5
```

**2. Integrate into FlavorPilotEvaluator**:
```python
# backend/app/evals/evaluator.py (FlavorPilotEvaluator)
response_time_score = ResponseTimeEvaluator().evaluate(trajectory)
```

---

## Troubleshooting

### Issue: Import Errors in Python

**Symptom**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Set PYTHONPATH
export PYTHONPATH=/workspace:$PYTHONPATH  # macOS/Linux
# or
$env:PYTHONPATH="/workspace;$env:PYTHONPATH"  # Windows PowerShell

# Or run from project root
cd /workspace
python -m backend.app.main
```

---

### Issue: Database Connection Refused

**Symptom**: `could not connect to server: Connection refused`

**Solution**:
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -U postgres

# Start PostgreSQL
brew services start postgresql@15  # macOS
sudo systemctl start postgresql    # Linux

# Check if database exists
psql -U postgres -l | grep flavorpilot
```

---

### Issue: Port Already in Use

**Symptom**: `Error: listen EADDRINUSE: address already in use :::5173`

**Solution**:
```bash
# Find process using port
lsof -i :5173

# Kill process
kill -9 <PID>

# Or use the stop script
./stop.sh
```

---

### Issue: MCP Client Timeouts

**Symptom**: `TimeoutError: MCP server did not respond`

**Solution**:
1. **Switch to Mock Client**:
   ```python
   # backend/app/config.py
   USE_MOCK_MCP = True
   ```

2. **Increase timeout**:
   ```python
   # backend/app/mcp/zomato_client.py
   self.timeout = 30  # Increase from 10 to 30 seconds
   ```

---

### Issue: Frontend Build Errors

**Symptom**: `Module not found: Error: Can't resolve '@/components/...'`

**Solution**:
```bash
# Clear cache
rm -rf node_modules/.vite
rm -rf node_modules

# Reinstall dependencies
npm install

# Restart dev server
npm run dev
```

---

## Contributing

### Pull Request Checklist

- [ ] Code follows style guide (Black, isort for Python; Prettier for TypeScript)
- [ ] All tests pass (`pytest` and `npm test`)
- [ ] New features have tests
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] PR description explains what and why

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Build process or auxiliary tool changes

**Example**:
```
feat(agents): Add review analysis worker

- Implemented ReviewAnalysisWorker for sentiment analysis
- Integrated with Lead Agent orchestration
- Added tests for positive/negative review classification

Closes #123
```

---

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **pgvector Docs**: https://github.com/pgvector/pgvector
- **MCP Spec**: https://modelcontextprotocol.io/

---

**Last Updated**: September 22, 2026  
**Version**: 1.0.0  
**Questions?** Open an issue on GitHub
