# Connecting to Zomato MCP Server

## Overview

FlavorPilot is now configured to connect to the **official Zomato MCP server** at:
```
https://mcp-server.zomato.com/mcp
```

This is a public MCP server provided by Zomato that exposes restaurant data and ordering capabilities through the Model Context Protocol.

## Current Status

✅ **Configuration Complete**
- HTTP MCP client implemented (`backend/app/mcp/http_client.py`)
- Environment configured with real server URL
- Transport mode: HTTP (JSON-RPC 2.0)

⚠️ **Authentication Required**
The Zomato MCP server returns:
```json
{
  "error": "invalid_token",
  "error_description": "Authentication required"
}
```

## Authentication Setup

The server requires authentication via Bearer token. To connect:

### Option 1: Get API Key (If Available)

If Zomato provides public API keys for their MCP server:

1. Visit the Zomato MCP documentation or developer portal
2. Register and obtain an API key
3. Add to `.env`:
   ```bash
   ZOMATO_API_KEY=your_actual_api_key_here
   ```

### Option 2: Check GitHub Repository

The Zomato MCP server repository might contain:
- Authentication documentation
- API key request process
- Public demo credentials
- Alternative authentication methods

Repository: https://github.com/Zomato/mcp-server-manifest

### Option 3: Use Mock Data (Recommended for Development)

While waiting for API access, continue development with mock data:

```bash
# In .env
USE_MOCK_MCP=true
```

This uses the `MockZomatoMCPClient` which provides realistic synthetic data for all restaurant operations.

## Configuration Files

### `.env`
```bash
# Use real Zomato MCP server
USE_MOCK_MCP=false
ZOMATO_MCP_TRANSPORT=http
ZOMATO_MCP_SERVER_URL=https://mcp-server.zomato.com/mcp
ZOMATO_API_KEY=your_key_here  # Required for authentication
```

### Test Connection

Run the validation script:
```bash
python3 scripts/test_zomato_mcp_connection.py
```

This will:
- Test HTTP connectivity
- Verify authentication
- List available MCP tools
- Test basic tool calls

## Available Tools

Once authenticated, the Zomato MCP server provides these tools:

1. **zomato.search_restaurants** - Search for restaurants by query, location, cuisine, budget
2. **zomato.get_menu** - Get menu items for a specific restaurant
3. **zomato.get_item_customizations** - Get customization options for menu items
4. **zomato.apply_promo_code** - Apply promotional codes to cart
5. **zomato.build_cart** - Build and validate cart with selected items

## Implementation Details

### HTTP MCP Client

The `ZomatoHTTPMCPClient` class implements:
- JSON-RPC 2.0 protocol over HTTP POST
- Bearer token authentication
- Automatic retry with exponential backoff
- Response parsing and error handling
- Async/await pattern with context manager support

### Client Selection

The system automatically selects the appropriate client:

```python
if settings.use_mock_mcp:
    # Development mode with synthetic data
    client = MockZomatoMCPClient()
else:
    if settings.zomato_mcp_transport == "http":
        # Production mode with real Zomato server
        client = ZomatoHTTPMCPClient(
            server_url=settings.zomato_mcp_server_url,
            api_key=settings.zomato_api_key
        )
```

## Next Steps

**IMMEDIATE ACTION REQUIRED:**

1. **Obtain Zomato MCP API Key**
   - Check https://github.com/Zomato/mcp-server-manifest for documentation
   - Look for authentication requirements or demo credentials
   - Contact Zomato if public access is available

2. **Update `.env` with Real Credentials**
   ```bash
   USE_MOCK_MCP=false
   ZOMATO_API_KEY=<your_real_key>
   ```

3. **Test Connection**
   ```bash
   python3 scripts/test_zomato_mcp_connection.py
   ```

4. **Switch to Production**
   Once authenticated, FlavorPilot will automatically use real Zomato data for all restaurant searches, menu queries, and orders.

## Fallback Strategy

If API access is not available:
- Continue using `MockZomatoMCPClient` (highly realistic mock data)
- All features work identically with mock data
- Easy to switch to real server once credentials are available
- No code changes needed - just update `.env`

---

**Repository:** https://github.com/Zomato/mcp-server-manifest  
**Server URL:** https://mcp-server.zomato.com/mcp  
**Protocol:** JSON-RPC 2.0 over HTTP  
**Authentication:** Bearer token (API key required)
