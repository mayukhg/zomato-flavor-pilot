"""HTTP transport wrapper for Zomato MCP server at https://mcp-server.zomato.com/mcp"""
import json
import logging
from typing import Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ZomatoHTTPMCPClient:
    """
    HTTP MCP client for Zomato's official public MCP server.
    
    Server: https://mcp-server.zomato.com/mcp
    Protocol: JSON-RPC 2.0 over HTTP POST
    
    Note: Server requires authentication. Set ZOMATO_API_KEY in environment.
    """
    
    def __init__(
        self, 
        server_url: str = "https://mcp-server.zomato.com/mcp", 
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.server_url = server_url
        self.api_key = api_key
        self.timeout = timeout
        self._session: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._request_id = 0
    
    async def connect(self) -> None:
        """Initialize HTTP client and test connection."""
        self._session = httpx.AsyncClient(timeout=self.timeout)
        self._connected = True  # Mark as connected before testing
        
        # Test connection by listing available tools
        try:
            tools = await self.list_tools()
            tool_names = [t.get("name") for t in tools]
            logger.info(f"✓ Connected to Zomato MCP server (HTTP)")
            logger.info(f"✓ Available tools: {', '.join(tool_names)}")
        except Exception as e:
            logger.error(f"Failed to connect to Zomato MCP server: {e}")
            self._connected = False
            if self._session:
                await self._session.aclose()
            raise
    
    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._connected = False
        logger.info("Disconnected from Zomato MCP server")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def _rpc_call(self, method: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Make JSON-RPC 2.0 call to MCP server."""
        if not self._session or not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")
        
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = await self._session.post(
                self.server_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                error_msg = result["error"].get("message", str(result["error"]))
                raise Exception(f"MCP server error: {error_msg}")
            
            return result.get("result", {})
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            if e.response.status_code == 401:
                logger.error("Authentication failed. Please check ZOMATO_API_KEY in .env")
            raise
        except Exception as e:
            logger.error(f"RPC call failed: {e}")
            raise
    
    async def list_tools(self) -> list[dict]:
        """List available MCP tools."""
        result = await self._rpc_call("tools/list")
        return result.get("tools", [])
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool with retry logic."""
        result = await self._rpc_call("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        
        # Extract content from MCP response
        if "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                # Get first text content
                for item in content:
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        # Try to parse as JSON
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            return text
            return content
        
        return result
    
    # Zomato-specific tool methods
    
    async def search_restaurants(
        self,
        query: str,
        location: str,
        cuisine: Optional[str] = None,
        max_delivery_mins: Optional[int] = None,
        budget_cap_inr: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Search for restaurants on Zomato."""
        args = {
            "query": query,
            "location": location,
        }
        if cuisine:
            args["cuisine"] = cuisine
        if max_delivery_mins:
            args["max_delivery_mins"] = max_delivery_mins
        if budget_cap_inr:
            args["budget_cap_inr"] = budget_cap_inr
        
        result = await self.call_tool("zomato.search_restaurants", args)
        return result if isinstance(result, list) else []
    
    async def get_menu(
        self,
        restaurant_id: str,
        dietary_filter: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get menu for a restaurant."""
        args = {"restaurant_id": restaurant_id}
        if dietary_filter:
            args["dietary_filter"] = dietary_filter
        
        return await self.call_tool("zomato.get_menu", args)
    
    async def get_item_customizations(self, item_id: str) -> dict[str, Any]:
        """Get customization options for a menu item."""
        return await self.call_tool("zomato.get_item_customizations", {"item_id": item_id})
    
    async def apply_promo_code(self, cart_id: str, promo_code: str) -> dict[str, Any]:
        """Apply promo code to cart."""
        return await self.call_tool("zomato.apply_promo_code", {
            "cart_id": cart_id,
            "promo_code": promo_code,
        })
    
    async def build_cart(
        self,
        items: list[dict[str, Any]],
        delivery_address: dict[str, str],
    ) -> dict[str, Any]:
        """Build a cart with selected items."""
        return await self.call_tool("zomato.build_cart", {
            "items": items,
            "delivery_address": delivery_address,
        })
