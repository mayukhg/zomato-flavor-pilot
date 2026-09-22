# Connecting to Zomato MCP Server

Complete guide for connecting FlavorPilot to a real Zomato MCP server instead of using mock data.

---

## Current Status

⚠️ **FlavorPilot is currently using MOCK data** - no real Zomato API calls are being made.

To use real Zomato data, you need to connect to an actual Zomato MCP server.

---

## Prerequisites

### 1. Zomato API Access

You'll need one of these:

**Option A: Official Zomato MCP Server** (Preferred)
- Contact Zomato for MCP server access
- Get API credentials and endpoint

**Option B: Zomato REST API** (Build your own bridge)
- Get Zomato API key from [Zomato Developers](https://developers.zomato.com/)
- Build MCP server that wraps their REST API

**Option C: Third-party MCP Server**
- Use a community-built Zomato MCP server (if available)

---

## Option A: Official Zomato MCP Server

### Step 1: Obtain Credentials

Contact Zomato to get:
```
ZOMATO_MCP_SERVER_URL=https://mcp.zomato.com/sse
ZOMATO_API_KEY=zm_live_abc123xyz789...
```

Or for stdio transport:
```
npm install @zomato/mcp-server
```

### Step 2: Configure Environment

Edit `/workspace/.env`:

```env
# Enable real MCP client
USE_MOCK_MCP=false

# Choose transport method
ZOMATO_MCP_TRANSPORT=sse  # or "stdio"

# For HTTP/SSE transport
ZOMATO_MCP_SERVER_URL=https://mcp.zomato.com/sse

# For stdio transport
ZOMATO_MCP_STDIO_CMD=npx -y @zomato/mcp-server

# Your real Zomato API key
ZOMATO_API_KEY=zm_live_your_actual_key_here
```

### Step 3: Restart Services

```bash
./stop.sh
./start.sh
```

The system will now connect to the real Zomato MCP server!

---

## Option B: Build Your Own MCP Bridge

If Zomato doesn't provide an MCP server, you can build one that wraps their REST API.

### Step 1: Get Zomato API Key

1. Go to [Zomato Developers](https://developers.zomato.com/)
2. Sign up / Log in
3. Create an application
4. Copy your API key: `zm_live_abc123...`

### Step 2: Create MCP Server Project

```bash
mkdir zomato-mcp-server
cd zomato-mcp-server
npm init -y
npm install @modelcontextprotocol/sdk express axios dotenv
```

### Step 3: Implement MCP Server

Create `index.js`:

```javascript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import axios from 'axios';

const ZOMATO_API_KEY = process.env.ZOMATO_API_KEY;
const ZOMATO_BASE_URL = 'https://developers.zomato.com/api/v2.1';

const server = new Server(
  {
    name: 'zomato-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool 1: Search Restaurants
server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;

  if (name === 'zomato.search_restaurants') {
    const { query, location, budget_cap_inr } = args;
    
    try {
      // Get location entity_id first
      const geoResponse = await axios.get(`${ZOMATO_BASE_URL}/geocode`, {
        headers: { 'user-key': ZOMATO_API_KEY },
        params: { lat: 12.9716, lon: 77.5946 } // Bangalore coords
      });
      
      // Search restaurants
      const searchResponse = await axios.get(`${ZOMATO_BASE_URL}/search`, {
        headers: { 'user-key': ZOMATO_API_KEY },
        params: {
          entity_id: geoResponse.data.location.entity_id,
          entity_type: 'city',
          q: query,
          sort: 'rating',
          order: 'desc'
        }
      });
      
      const restaurants = searchResponse.data.restaurants.map(r => ({
        restaurant_id: r.restaurant.id,
        name: r.restaurant.name,
        cuisine: r.restaurant.cuisines,
        location: r.restaurant.location.address,
        rating: r.restaurant.user_rating.aggregate_rating,
        price_for_two: r.restaurant.average_cost_for_two,
        delivery_available: r.restaurant.has_online_delivery
      }));
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(restaurants)
          }
        ]
      };
    } catch (error) {
      throw new Error(`Zomato API error: ${error.message}`);
    }
  }
  
  // Tool 2: Get Menu
  if (name === 'zomato.get_menu') {
    const { restaurant_id } = args;
    
    const response = await axios.get(`${ZOMATO_BASE_URL}/dailymenu`, {
      headers: { 'user-key': ZOMATO_API_KEY },
      params: { res_id: restaurant_id }
    });
    
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(response.data.daily_menus)
        }
      ]
    };
  }
  
  // Add other tools: get_item_customizations, apply_promo_code, build_cart
  // ...
  
  throw new Error(`Unknown tool: ${name}`);
});

// List available tools
server.setRequestHandler('tools/list', async () => {
  return {
    tools: [
      {
        name: 'zomato.search_restaurants',
        description: 'Search for restaurants on Zomato',
        inputSchema: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Search query' },
            location: { type: 'string', description: 'Location' },
            budget_cap_inr: { type: 'number', description: 'Max budget' }
          },
          required: ['query', 'location']
        }
      },
      {
        name: 'zomato.get_menu',
        description: 'Get menu for a restaurant',
        inputSchema: {
          type: 'object',
          properties: {
            restaurant_id: { type: 'string', description: 'Restaurant ID' }
          },
          required: ['restaurant_id']
        }
      }
      // Add other tools...
    ]
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Zomato MCP server running on stdio');
}

main().catch(console.error);
```

### Step 4: Configure FlavorPilot

Edit `/workspace/.env`:

```env
USE_MOCK_MCP=false
ZOMATO_MCP_TRANSPORT=stdio
ZOMATO_MCP_STDIO_CMD=node /path/to/zomato-mcp-server/index.js
ZOMATO_API_KEY=zm_live_your_actual_key_here
```

### Step 5: Test Your MCP Server

```bash
# Test the MCP server directly
node index.js

# In another terminal, test with MCP client
npx @modelcontextprotocol/inspector node index.js
```

---

## Option C: HTTP/SSE Transport

If you prefer HTTP/SSE instead of stdio:

### Step 1: Create HTTP MCP Server

```javascript
// http-server.js
import express from 'express';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';

const app = express();
app.use(express.json());

app.post('/sse', async (req, res) => {
  const transport = new SSEServerTransport('/messages', res);
  await server.connect(transport);
});

app.listen(8080, () => {
  console.log('Zomato MCP server running on http://localhost:8080');
});
```

### Step 2: Configure FlavorPilot

```env
USE_MOCK_MCP=false
ZOMATO_MCP_TRANSPORT=sse
ZOMATO_MCP_SERVER_URL=http://localhost:8080/sse
```

---

## Code Changes Required

The following files need to be updated to support real MCP connection:

### 1. Update `backend/app/config.py`

✅ Already done - see updated file

### 2. Update `backend/app/agents/orchestrator.py`

✅ Already done - see updated file

### 3. Update `backend/app/mcp/zomato_client.py`

✅ Already done - client supports both transports

---

## Testing the Connection

### Step 1: Check Environment

```bash
cd /workspace
cat .env | grep MCP
```

Should show:
```
USE_MOCK_MCP=false
ZOMATO_MCP_TRANSPORT=stdio
ZOMATO_MCP_STDIO_CMD=...
```

### Step 2: Start Services

```bash
./start.sh
```

Watch for logs:
```
✓ Connected to Zomato MCP server (stdio)
✓ 5/5 tools available
```

### Step 3: Test Search Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "pizza",
    "location": "Koramangala, Bangalore"
  }'
```

Should return REAL restaurants from Zomato!

### Step 4: Verify in UI

1. Open http://localhost:5173
2. Enter: "Find pizza places near me"
3. Check that real restaurant names appear (not "Green Theory Kitchen")

---

## Troubleshooting

### Issue 1: "MCP Connection Failed"

**Check:**
```bash
# Is MCP server running?
ps aux | grep mcp-server

# Test MCP server directly
node /path/to/zomato-mcp-server/index.js
```

**Solution:**
- Verify `ZOMATO_MCP_STDIO_CMD` path is correct
- Check MCP server logs for errors
- Ensure Zomato API key is valid

---

### Issue 2: "API Key Invalid"

**Error:**
```
403 Forbidden: Invalid API Key
```

**Solution:**
1. Verify API key in `.env`
2. Check key hasn't expired on Zomato dashboard
3. Ensure key has correct permissions

---

### Issue 3: "No Restaurants Found"

**Possible Causes:**
- Location not recognized by Zomato
- Search query too specific
- No restaurants in that area

**Solution:**
```bash
# Test with broad query
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurant",
    "location": "Bangalore"
  }'
```

---

### Issue 4: "MCP Tools Not Available"

**Check tool list:**
```bash
# Use MCP inspector
npx @modelcontextprotocol/inspector node /path/to/mcp-server/index.js
```

Should show:
```
Available tools:
✓ zomato.search_restaurants
✓ zomato.get_menu
✓ zomato.get_item_customizations
✓ zomato.apply_promo_code
✓ zomato.build_cart
```

---

## Verifying Real Data

### Mock Data Indicators (Current):
- Restaurant names: "Green Theory Kitchen", "Fuel & Fire"
- Always 2 restaurants
- Static prices: ₹389, ₹349
- Warning log: "Using MOCK Zomato MCP client"

### Real Data Indicators (After Setup):
- Restaurant names vary by location
- Dynamic number of results
- Real prices from Zomato
- Log: "Connected to Zomato MCP server"
- Real ratings and reviews
- Actual delivery times

---

## Production Considerations

### 1. API Rate Limits

Zomato API typically has rate limits:
- 1,000 calls/day (free tier)
- 100,000 calls/day (paid tier)

**Implement caching:**
```python
# backend/app/mcp/zomato_client.py
from functools import lru_cache
from datetime import timedelta

@lru_cache(maxsize=1000)
async def search_restaurants_cached(query: str, location: str):
    # Cache results for 5 minutes
    return await real_client.search_restaurants(query, location)
```

### 2. Error Handling

```python
# Fallback to mock if real API fails
try:
    restaurants = await real_client.search_restaurants(...)
except ZomatoAPIError as e:
    logger.error(f"Zomato API failed: {e}")
    # Fallback to mock or cached data
    restaurants = await mock_client.search_restaurants(...)
```

### 3. Monitoring

Track:
- API response times
- Error rates
- Rate limit usage
- Cost per query

### 4. Security

- Store API keys in secure vault (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys regularly
- Use HTTPS for SSE transport
- Validate all API responses

---

## Cost Estimates

**Zomato API Pricing** (approximate):
- Free tier: 1,000 calls/day
- Paid tier: $0.001 per call

**FlavorPilot Usage**:
- Simple query: 1-2 API calls
- Complex group query: 5-8 API calls
- Cost per user query: $0.001 - $0.008

**100 users/day = $0.10 - $0.80/day**

---

## Summary Checklist

To connect to real Zomato MCP server:

- [ ] Obtain Zomato API credentials
- [ ] Choose transport method (stdio or HTTP/SSE)
- [ ] Update `.env` with real credentials
- [ ] Set `USE_MOCK_MCP=false`
- [ ] Restart services (`./stop.sh && ./start.sh`)
- [ ] Test with real query in UI
- [ ] Verify real restaurant data appears
- [ ] Monitor logs for connection success
- [ ] Implement caching for production
- [ ] Set up error handling and fallbacks

---

## Next Steps

1. **Get Zomato API Access** - Priority #1
2. **Build or Deploy MCP Server** - If needed
3. **Update Configuration** - Set environment variables
4. **Test Connection** - Verify real data
5. **Deploy to Production** - With proper monitoring

---

**Questions?**
- Zomato API docs: https://developers.zomato.com/documentation
- MCP Protocol spec: https://modelcontextprotocol.io/
- FlavorPilot issues: https://github.com/mayukhg/zomato-flavor-pilot/issues

---

**Last Updated**: September 22, 2026  
**Version**: 1.0.0
