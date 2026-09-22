# Cursor MCP Configuration Files

This directory contains example MCP configuration files for native Cursor IDE integration with the Zomato MCP server.

## Files

### `mcp.json` - Basic Configuration (No Authentication)
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

Use this if the Zomato MCP server allows unauthenticated access or public demo mode.

### `mcp.auth.json` - Authenticated Configuration
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

Use this if you have a Zomato API key for the MCP server.

## How to Use

### Copy to Cursor Settings Directory

**macOS:**
```bash
cp mcp.json ~/Library/Application\ Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp.json
```

**Windows (PowerShell):**
```powershell
Copy-Item mcp.json $env:APPDATA\Cursor\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp.json
```

**Linux:**
```bash
cp mcp.json ~/.config/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp.json
```

### Restart Cursor

After copying the configuration, restart Cursor to load the MCP server connection.

## Documentation

For complete setup instructions, see:
- **[Cursor MCP Integration Guide](../docs/CURSOR_MCP_INTEGRATION.md)** - Native Cursor IDE integration
- **[Zomato MCP Setup](../docs/ZOMATO_MCP_SETUP.md)** - Python backend integration

## Notes

- These configurations connect to the **official hosted Zomato MCP server**
- No local server or Python environment required for Cursor integration
- Authentication (API key) may be required - check with Zomato
- The server URL is: `https://mcp-server.zomato.com/mcp`
- Transport type: SSE (Server-Sent Events)
