"""Zomato MCP Client Bridge with dual transport support (stdio/SSE)."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Literal, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.config import settings

logger = logging.getLogger(__name__)


class ZomatoMCPError(Exception):
    """Base exception for Zomato MCP operations."""
    pass


class ZomatoMCPConnectionError(ZomatoMCPError):
    """Raised when MCP server connection fails."""
    pass


class ZomatoMCPToolError(ZomatoMCPError):
    """Raised when MCP tool execution fails."""
    pass


class ZomatoMCPClient:
    """
    MCP client for Zomato server with automatic transport selection.
    
    Supports:
    - stdio transport: spawns MCP server as subprocess
    - SSE transport: connects to HTTP endpoint
    
    Usage:
        async with ZomatoMCPClient() as client:
            results = await client.search_restaurants(
                query="Keto Bowl",
                location="Indiranagar",
                budget_cap_inr=500.0
            )
    """
    
    def __init__(
        self,
        transport: Optional[Literal["stdio", "sse"]] = None,
        stdio_cmd: Optional[str] = None,
        server_url: Optional[str] = None,
    ):
        """
        Initialize Zomato MCP client.
        
        Args:
            transport: Transport mode ("stdio" or "sse"). Defaults to settings.
            stdio_cmd: Command to spawn MCP server for stdio transport.
            server_url: URL for SSE transport.
        """
        self.transport = transport or settings.zomato_mcp_transport
        self.stdio_cmd = stdio_cmd or settings.zomato_mcp_stdio_cmd
        self.server_url = server_url or settings.zomato_mcp_server_url
        
        self._session: Optional[ClientSession] = None
        self._read_stream: Optional[Any] = None
        self._write_stream: Optional[Any] = None
        self._connected = False
    
    @asynccontextmanager
    async def _get_transport_context(self) -> AsyncGenerator[tuple[Any, Any], None]:
        """Get appropriate transport context manager based on configuration."""
        if self.transport == "stdio":
            command, *args = self.stdio_cmd.split()
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=None,
            )
            async with stdio_client(server_params) as (read, write):
                yield read, write
        elif self.transport == "sse":
            async with sse_client(self.server_url) as (read, write):
                yield read, write
        else:
            raise ZomatoMCPConnectionError(
                f"Unsupported transport: {self.transport}. Use 'stdio' or 'sse'."
            )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def connect(self) -> None:
        """Establish connection to Zomato MCP server with retry logic."""
        if self._connected:
            logger.warning("MCP client already connected")
            return
        
        try:
            logger.info(f"Connecting to Zomato MCP server via {self.transport}")
            
            # Get transport streams
            self._transport_context = self._get_transport_context()
            self._read_stream, self._write_stream = await self._transport_context.__aenter__()
            
            # Create session
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.__aenter__()
            
            # Initialize session
            await self._session.initialize()
            
            self._connected = True
            logger.info("Successfully connected to Zomato MCP server")
            
        except Exception as e:
            logger.error(f"Failed to connect to Zomato MCP server: {e}")
            await self._cleanup()
            raise ZomatoMCPConnectionError(f"MCP connection failed: {e}") from e
    
    async def disconnect(self) -> None:
        """Close MCP connection gracefully."""
        if not self._connected:
            return
        
        logger.info("Disconnecting from Zomato MCP server")
        await self._cleanup()
        self._connected = False
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            self._session = None
        
        if hasattr(self, '_transport_context'):
            try:
                await self._transport_context.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing transport: {e}")
    
    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call MCP tool with error handling.
        
        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments
            
        Returns:
            Tool result data
            
        Raises:
            ZomatoMCPToolError: If tool execution fails
        """
        if not self._connected or not self._session:
            raise ZomatoMCPConnectionError("MCP client not connected")
        
        try:
            logger.debug(f"Calling tool '{tool_name}' with args: {arguments}")
            result = await self._session.call_tool(tool_name, arguments)
            
            if hasattr(result, 'content') and result.content:
                # Extract text content from MCP response
                content = result.content[0]
                if hasattr(content, 'text'):
                    return json.loads(content.text)
                return content
            
            return result
            
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            raise ZomatoMCPToolError(f"Tool execution failed: {e}") from e
    
    # ===== Zomato MCP Tool Methods =====
    
    async def search_restaurants(
        self,
        query: str,
        location: str,
        cuisine: Optional[str] = None,
        max_delivery_mins: Optional[int] = None,
        budget_cap_inr: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for restaurants matching criteria.
        
        Args:
            query: Search query (e.g., "Keto Bowl", "Biryani")
            location: Delivery location (e.g., "Indiranagar", "Koramangala")
            cuisine: Optional cuisine filter
            max_delivery_mins: Maximum delivery time in minutes
            budget_cap_inr: Maximum budget per item in INR
            
        Returns:
            List of restaurant objects with ratings, ETA, fees
        """
        arguments = {
            "query": query,
            "location": location,
        }
        
        if cuisine:
            arguments["cuisine"] = cuisine
        if max_delivery_mins:
            arguments["max_delivery_mins"] = max_delivery_mins
        if budget_cap_inr:
            arguments["budget_cap_inr"] = budget_cap_inr
        
        return await self._call_tool("zomato.search_restaurants", arguments)
    
    async def get_menu(
        self,
        restaurant_id: str,
        dietary_filter: Optional[Literal["vegan", "keto", "halal", "nut_free"]] = None,
    ) -> dict[str, Any]:
        """
        Get restaurant menu with optional dietary filtering.
        
        Args:
            restaurant_id: Restaurant identifier
            dietary_filter: Optional dietary constraint filter
            
        Returns:
            Menu structure with items, ingredients, allergen tags
        """
        arguments = {"restaurant_id": restaurant_id}
        
        if dietary_filter:
            arguments["dietary_filter"] = dietary_filter
        
        return await self._call_tool("zomato.get_menu", arguments)
    
    async def get_item_customizations(
        self,
        item_id: str,
    ) -> dict[str, Any]:
        """
        Get available customizations for a menu item.
        
        Args:
            item_id: Menu item identifier
            
        Returns:
            Customization options (portion size, spice level, add-ons)
        """
        arguments = {"item_id": item_id}
        return await self._call_tool("zomato.get_item_customizations", arguments)
    
    async def apply_promo_code(
        self,
        cart_id: str,
        promo_code: str,
    ) -> dict[str, Any]:
        """
        Apply promotional code to cart.
        
        Args:
            cart_id: Cart identifier
            promo_code: Promo code to apply
            
        Returns:
            Updated cart with discount applied
        """
        arguments = {
            "cart_id": cart_id,
            "promo_code": promo_code,
        }
        return await self._call_tool("zomato.apply_promo_code", arguments)
    
    async def build_cart(
        self,
        items: list[dict[str, Any]],
        delivery_address: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build and stage a cart for approval.
        
        Args:
            items: List of items with customizations
            delivery_address: Delivery address details
            
        Returns:
            Staged cart token ready for approval
        """
        arguments = {
            "items": items,
            "delivery_address": delivery_address,
        }
        return await self._call_tool("zomato.build_cart", arguments)


# ===== Mock Fallback Client =====

class MockZomatoMCPClient(ZomatoMCPClient):
    """Mock client for development without live MCP server."""
    
    async def connect(self) -> None:
        """Mock connection."""
        logger.warning("Using MOCK Zomato MCP client (no real server)")
        self._connected = True
    
    async def disconnect(self) -> None:
        """Mock disconnection."""
        self._connected = False
    
    async def search_restaurants(self, query: str, location: str, **kwargs) -> list[dict[str, Any]]:
        """Return mock restaurant data."""
        return [
            {
                "restaurant_id": "mock_rest_001",
                "name": "Green Theory Kitchen",
                "cuisine": "Contemporary Indian",
                "location": location,
                "rating": 4.7,
                "eta_mins": 25,
                "delivery_fee_inr": 29,
                "tags": ["allergen_verified", "nut_free"],
            },
            {
                "restaurant_id": "mock_rest_002",
                "name": "Fuel & Fire",
                "cuisine": "High-protein bowls",
                "location": location,
                "rating": 4.6,
                "eta_mins": 30,
                "delivery_fee_inr": 0,
                "tags": ["macro_verified", "keto"],
            },
        ]
    
    async def get_menu(self, restaurant_id: str, **kwargs) -> dict[str, Any]:
        """Return mock menu data."""
        return {
            "restaurant_id": restaurant_id,
            "categories": [
                {
                    "name": "Bowls",
                    "items": [
                        {
                            "item_id": "item_001",
                            "name": "Keto Tandoori Power Bowl",
                            "price_inr": 389,
                            "protein_g": 45,
                            "carbs_g": 12,
                            "fat_g": 28,
                            "tags": ["keto", "high_protein"],
                        },
                        {
                            "item_id": "item_002",
                            "name": "Vegan Green Curry Bowl",
                            "price_inr": 349,
                            "protein_g": 18,
                            "carbs_g": 52,
                            "fat_g": 14,
                            "tags": ["vegan", "nut_free"],
                        },
                    ],
                },
            ],
        }
    
    async def get_item_customizations(self, item_id: str) -> dict[str, Any]:
        """Return mock customization options."""
        return {
            "item_id": item_id,
            "customizations": [
                {
                    "group": "portion_size",
                    "options": [
                        {"id": "regular", "name": "Regular", "price_delta": 0},
                        {"id": "large", "name": "Large", "price_delta": 50},
                    ],
                },
                {
                    "group": "spice_level",
                    "options": [
                        {"id": "mild", "name": "Mild"},
                        {"id": "medium", "name": "Medium"},
                        {"id": "spicy", "name": "Spicy"},
                    ],
                },
            ],
        }
    
    async def apply_promo_code(self, cart_id: str, promo_code: str) -> dict[str, Any]:
        """Return mock promo application result."""
        return {
            "cart_id": cart_id,
            "promo_code": promo_code,
            "discount_inr": 240,
            "status": "applied",
        }
    
    async def build_cart(self, items: list[dict], delivery_address: dict) -> dict[str, Any]:
        """Return mock cart build result."""
        return {
            "cart_id": f"cart_{hash(str(items))}_mock",
            "items": items,
            "delivery_address": delivery_address,
            "subtotal_inr": 1067,
            "status": "staged",
        }
