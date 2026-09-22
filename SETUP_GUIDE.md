# FlavorPilot Setup & Deployment Guide

## Prerequisites

### Required Software
- **Python 3.12+**: Backend runtime
- **Node.js 18+** & **Bun**: Frontend build tools
- **PostgreSQL 14+** with **pgvector** extension: Database
- **Optional**: Zomato MCP Server (mock client available for development)

### PostgreSQL Setup

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install pgvector extension
sudo apt install postgresql-14-pgvector

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres psql -c "CREATE DATABASE flavorpilot;"
sudo -u postgres psql -d flavorpilot -c "CREATE EXTENSION vector;"

# Set password for postgres user (optional)
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd flavorpilot
```

### 2. Backend Setup

```bash
# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Create .env file from template
cp .env.example .env

# Edit .env with your configuration
# At minimum, set DATABASE_URL
nano .env
```

### 3. Frontend Setup

```bash
# Install Node dependencies
npm install

# Or using Bun
bun install
```

### 4. Generate Golden Dataset

```bash
# Generate 100 synthetic evaluation test cases
python seed_data_flavorpilot.py

# This creates: /workspace/scratch/golden_dataset_flavorpilot.json
```

### 5. Initialize Database

```bash
# Seed database with golden dataset
python scripts/seed_database.py

# This creates tables and inserts evaluation cases
```

## Running the Application

### Development Mode

#### Option 1: Automated Startup (Recommended)

```bash
# Start both backend and frontend
./start.sh
```

This will:
1. Check PostgreSQL connection
2. Create database if needed
3. Generate golden dataset
4. Seed database
5. Start FastAPI backend on port 8000
6. Start Vite frontend on port 5173

#### Option 2: Manual Startup

**Terminal 1 - Backend:**
```bash
cd backend
python -m app.main
```

**Terminal 2 - Frontend:**
```bash
npm run dev
# Or: bun run dev
```

### Production Mode

```bash
# Build frontend
npm run build

# Run production backend with Gunicorn
cd backend
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

## Application URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/openapi.json

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flavorpilot

# Zomato MCP Server
ZOMATO_MCP_TRANSPORT=stdio  # or "sse"
ZOMATO_MCP_STDIO_CMD=node /path/to/zomato-mcp-server/dist/index.js
ZOMATO_MCP_SERVER_URL=http://localhost:8080/sse
ZOMATO_API_KEY=zm_live_secret_key

# FastAPI Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Model Router
SMART_INTERN_MODEL=meta-llama/llama-3.3-70b-instruct
PHD_REASONER_MODEL=anthropic/claude-sonnet-4
ROUTING_THRESHOLD=0.75
```

### Frontend Configuration

Create `src/.env`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

## MCP Server Integration

### Using Mock MCP Client (Development)

The application includes a `MockZomatoMCPClient` that returns synthetic data without requiring a live MCP server. This is enabled by default in `backend/app/agents/orchestrator.py`.

### Connecting Real Zomato MCP Server

#### stdio Transport

```env
ZOMATO_MCP_TRANSPORT=stdio
ZOMATO_MCP_STDIO_CMD=node /path/to/zomato-mcp-server/dist/index.js
```

#### HTTP/SSE Transport

```env
ZOMATO_MCP_TRANSPORT=sse
ZOMATO_MCP_SERVER_URL=http://localhost:8080/sse
```

Update `backend/app/agents/orchestrator.py` line 99 to use real client:

```python
# Replace:
mcp_client = MockZomatoMCPClient()

# With:
mcp_client = ZomatoMCPClient()
```

## Architecture Overview

### Backend Components

```
backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Pydantic settings
│   ├── schemas.py              # API request/response models
│   ├── api/v1/                 # API routes
│   │   ├── search.py           # Restaurant search endpoint
│   │   ├── trajectory.py       # Agent execution logs
│   │   ├── cart.py             # Cart management
│   │   └── evals.py            # Evaluation endpoints
│   ├── agents/
│   │   └── orchestrator.py     # Lead-Worker agent engine
│   ├── evals/
│   │   └── evaluator.py        # RAG Triad & safety checks
│   └── mcp/
│       └── zomato_client.py    # MCP client bridge
└── db/
    ├── models.py               # SQLAlchemy models
    └── connection.py           # Database session management
```

### Frontend Components

```
src/
├── components/
│   └── flavorpilot/
│       └── flavor-pilot-app.tsx    # Main UI component
├── services/
│   └── api.ts                      # Typed API client
└── hooks/
    └── useFlavorPilot.ts           # React Query hooks
```

## API Endpoints

### Search

**POST** `/api/v1/search`
```json
{
  "query": "Keto Bowl",
  "location": "Indiranagar",
  "budget_cap_inr": 500,
  "group_size": 6,
  "dietary_constraints": ["Keto", "Vegan", "Nut-Free"]
}
```

### Agent Trajectory

**GET** `/api/v1/agent/trajectory/{session_id}`

Returns Lead-Worker execution steps with timing and costs.

### Cart Management

**POST** `/api/v1/cart/build`
```json
{
  "session_id": "session_abc123",
  "restaurant_id": "zomato_rest_001",
  "items": [...],
  "delivery_address": {...},
  "promo_code": "CBUSER"
}
```

**POST** `/api/v1/cart/approve`
```json
{
  "cart_id": "cart_xyz789",
  "allergen_confirmed": true
}
```

### Evaluations

**GET** `/api/v1/evals/summary`

Returns aggregate evaluation metrics:
- Total cases run
- Pass/fail counts
- Average groundedness & safety scores
- Total cost

**GET** `/api/v1/evals/cases?slice=Allergen%20Safety&limit=20`

List golden dataset test cases.

## Testing

### Run Backend Tests

```bash
cd backend
pytest
```

### Manual Testing Flow

1. **Generate Dataset**: `python seed_data_flavorpilot.py`
2. **Seed Database**: `python scripts/seed_database.py`
3. **Start Services**: `./start.sh`
4. **Open Frontend**: http://localhost:5173
5. **Test Search**: Enter "Group lunch for 6 under ₹2,000 — 3 keto, 1 vegan"
6. **View Trajectory**: Check Lead-Worker orchestration steps
7. **Build Cart**: Select restaurant and items
8. **Approve Cart**: Confirm allergen safety and approve

### Verification Checklist

- [ ] Golden dataset generated (100 cases)
- [ ] Database seeded successfully
- [ ] Backend health check passes: http://localhost:8000/health
- [ ] Frontend loads without errors
- [ ] Search returns restaurant results
- [ ] Agent trajectory displays Lead + Worker steps
- [ ] Cart builds with correct pricing
- [ ] Cart approval flow works
- [ ] Evaluation summary shows metrics

## Troubleshooting

### PostgreSQL Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Fix**: Start PostgreSQL service
```bash
sudo systemctl start postgresql
```

### MCP Connection Timeout

```
ZomatoMCPConnectionError: MCP connection failed
```

**Fix**: Use mock client for development (already configured) or verify MCP server is running.

### Frontend API Errors

```
Failed to fetch: http://localhost:8000/api/v1/search
```

**Fix**: Ensure backend is running on port 8000. Check CORS settings in `backend/app/config.py`.

### Missing pgvector Extension

```
sqlalchemy.exc.ProgrammingError: type "vector" does not exist
```

**Fix**: Install pgvector extension
```bash
sudo apt install postgresql-14-pgvector
sudo -u postgres psql -d flavorpilot -c "CREATE EXTENSION vector;"
```

## Production Deployment

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: ankane/pgvector
    environment:
      POSTGRES_DB: flavorpilot
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres:5432/flavorpilot
    depends_on:
      - postgres
  
  frontend:
    build: .
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  pgdata:
```

### Environment-Specific Configuration

Create `.env.production`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.example.com:5432/flavorpilot
ZOMATO_MCP_SERVER_URL=https://mcp.zomato.com/sse
ZOMATO_API_KEY=${ZOMATO_PRODUCTION_KEY}
CORS_ORIGINS=https://flavorpilot.example.com
```

## Security Considerations

1. **Never commit `.env` files** containing real API keys
2. **Use HTTPS in production** for all API communication
3. **Implement rate limiting** on public API endpoints
4. **Rotate API keys regularly**
5. **Enable PostgreSQL SSL** for production databases
6. **Sanitize user inputs** to prevent SQL/prompt injection
7. **Implement proper authentication** (OAuth, JWT) before production deployment

## Performance Optimization

### Database Indexing

```sql
CREATE INDEX idx_eval_cases_slice ON eval_cases(slice);
CREATE INDEX idx_trajectories_session ON agent_trajectories(session_id);
CREATE INDEX idx_carts_status ON carts(status);
```

### Caching Strategy

- Use Redis for session data
- Cache MCP responses for common queries
- Enable HTTP caching headers

### Model Routing

Adjust routing threshold in `.env` to optimize cost vs. accuracy:

```env
ROUTING_THRESHOLD=0.75  # Higher = more Smart Intern usage (cheaper)
```

## License

[Add license information]

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [docs-url]
- Email: support@flavorpilot.example.com
