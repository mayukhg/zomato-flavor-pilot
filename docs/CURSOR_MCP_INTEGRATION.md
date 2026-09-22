# Native Cursor MCP Integration Guide

## 🎯 Overview

This guide shows how to connect **Cursor IDE** directly to the official Zomato MCP server using native MCP support - **no Python scripts, no local environment files required**.

---

## 🚀 Quick Setup

### Step 1: Add MCP Configuration to Cursor

Add this configuration to your Cursor `mcp.json` file:

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

### Step 2: Locate Your Cursor MCP Config File

**File Location by OS:**

- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp.json`
- **Windows**: `%APPDATA%\Cursor\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp.json`
- **Linux**: `~/.config/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp.json`

**Or use Cursor UI:**
1. Open Cursor Settings (⌘+, on Mac, Ctrl+, on Windows/Linux)
2. Navigate to **Features** → **Model Context Protocol**
3. Click **Edit Config**

### Step 3: Restart Cursor

After saving the configuration, restart Cursor to load the MCP server.

---

## 🔐 Authentication (If Required)

If the Zomato MCP server requires authentication, use this configuration:

```json
{
  "mcpServers": {
    "zomato-mcp-server": {
      "url": "https://mcp-server.zomato.com/mcp",
      "transport": {
        "type": "sse"
      },
      "headers": {
        "Authorization": "Bearer YOUR_ZOMATO_API_KEY"
      }
    }
  }
}
```

**Getting an API Key:**
- Check the [Zomato MCP repository](https://github.com/Zomato/mcp-server-manifest) for API key registration
- Contact Zomato for enterprise/partner access
- See `docs/ZOMATO_MCP_SETUP.md` for alternative approaches

---

## ✅ Verify Connection

After restarting Cursor:

1. Open the **MCP Tool Picker** in Cursor
2. Look for Zomato tools:
   - `zomato.search_restaurants`
   - `zomato.get_menu`
   - `zomato.get_item_customizations`
   - `zomato.apply_promo_code`
   - `zomato.build_cart`

3. Test a tool by asking Cursor AI:
   ```
   Use the zomato.search_restaurants tool to find pizza places in Bangalore
   ```

---

## 📂 Example Configurations

We've included example configurations in this repository:

### Basic (No Auth)
```
.cursor/mcp.json
```

### With Authentication
```
.cursor/mcp.auth.json
```

**Usage:**
```bash
# Copy the appropriate config to your Cursor settings directory
cp .cursor/mcp.json ~/Library/Application\ Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp.json
```

---

## 🔄 Two Integration Approaches

### Approach 1: Native Cursor MCP (This Guide)
**Use when:**
- Working in Cursor IDE
- Want direct tool access in chat
- No backend integration needed
- Quick testing and exploration

**Benefits:**
- Zero setup, just config file
- Native Cursor UI integration
- Direct tool invocation in chat
- No Python environment required

### Approach 2: Python MCP Client (Backend Integration)
**Use when:**
- Building FlavorPilot backend
- Need programmatic API access
- Running autonomous agents
- Production deployment

**See:** `docs/ZOMATO_MCP_SETUP.md` for Python client approach

---

## 🛠️ Troubleshooting

### MCP Server Not Appearing

1. **Check config file syntax:**
   ```bash
   cat ~/Library/Application\ Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp.json | jq .
   ```

2. **Verify file location:**
   - Ensure you're editing the correct `mcp.json` file
   - File must be valid JSON (no trailing commas)

3. **Check Cursor logs:**
   - Open Cursor Developer Tools (Help → Toggle Developer Tools)
   - Look for MCP connection errors in Console

### 401 Unauthorized Error

- The server requires authentication
- Use the authenticated configuration with `Authorization` header
- Obtain a valid API key from Zomato

### SSE Connection Timeout

- Check network connectivity to `https://mcp-server.zomato.com/mcp`
- Verify no corporate firewall is blocking SSE connections
- Try from a different network

---

## 📊 Available Zomato MCP Tools

Once connected, you'll have access to:

### 1. `zomato.search_restaurants`
Search for restaurants with filters

**Parameters:**
- `query` (string): Search term (e.g., "Pizza", "Keto Bowl")
- `location` (string): City or area (e.g., "Bangalore", "Indiranagar")
- `cuisine` (string, optional): Cuisine filter
- `max_delivery_mins` (integer, optional): Maximum delivery time
- `budget_cap_inr` (number, optional): Budget limit in INR

### 2. `zomato.get_menu`
Get menu for a specific restaurant

**Parameters:**
- `restaurant_id` (string): Restaurant identifier
- `dietary_filter` (string, optional): Filter by diet (vegan, keto, halal, nut_free)

### 3. `zomato.get_item_customizations`
Get customization options for a menu item

**Parameters:**
- `item_id` (string): Menu item identifier

### 4. `zomato.apply_promo_code`
Apply promo code to cart

**Parameters:**
- `cart_id` (string): Cart identifier
- `promo_code` (string): Promotional code

### 5. `zomato.build_cart`
Build cart with selected items

**Parameters:**
- `items` (array): Array of item objects with customizations
- `delivery_address` (object): Delivery address details

---

## 🎯 Example Usage in Cursor

Once configured, you can use natural language:

```
Find me vegetarian restaurants in Bangalore under ₹500 budget
```

```
Get the menu for restaurant ID rest_123 with vegan filter
```

```
Build a cart with these items and deliver to Koramangala
```

Cursor will automatically invoke the appropriate Zomato MCP tools!

---

## 🔗 Resources

- **Zomato MCP Server:** https://mcp-server.zomato.com/mcp
- **Zomato MCP Repository:** https://github.com/Zomato/mcp-server-manifest
- **Model Context Protocol Spec:** https://modelcontextprotocol.io
- **Cursor MCP Docs:** https://docs.cursor.com/context/model-context-protocol

---

## 📝 Notes

- **Transport Type:** SSE (Server-Sent Events) is used for the remote HTTP endpoint
- **No Local Server:** You're connecting to Zomato's hosted MCP server, not running one locally
- **Authentication:** Currently returns 401, indicating API key is required
- **Fallback:** If you can't get API access, use the Python mock client for development

---

**Last Updated:** Tuesday, Sep 22, 2026  
**Server URL:** https://mcp-server.zomato.com/mcp  
**Transport:** SSE (Server-Sent Events)
