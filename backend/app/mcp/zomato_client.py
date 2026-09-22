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

# Official Zomato MCP tool names, with the names this app used to call first.
TOOL_ALIASES: dict[str, list[str]] = {
    "search_restaurants": ["get_restaurants_for_keyword", "search_restaurants", "zomato.search_restaurants"],
    "get_menu": ["get_menu_items_listing", "get_restaurant_menu_by_categories", "get_menu", "zomato.get_menu"],
    "get_saved_addresses": ["get_saved_addresses_for_user"],
    "get_item_customizations": ["get_item_customizations", "zomato.get_item_customizations"],
    "create_cart": ["create_cart", "add_to_cart", "zomato.build_cart", "build_cart"],
    "apply_promo_code": ["apply_promo_code", "zomato.apply_promo_code"],
}

ARGUMENT_ALIASES: dict[str, list[str]] = {
    "query": ["keyword", "query", "q", "search_query", "prompt", "text"],
    "location": ["location", "area", "city", "locality", "place"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lng", "lon", "long"],
    "cuisine": ["cuisine", "cuisines"],
    "max_delivery_mins": ["max_delivery_mins", "max_delivery_time", "delivery_time"],
    "budget_cap_inr": ["budget_cap_inr", "budget", "max_budget", "price_cap"],
    "restaurant_id": ["res_id", "restaurant_id", "restaurantId", "id"],
    "address_id": ["address_id", "addressId"],
    "filter": ["filter"],
    "dietary_filter": ["dietary_filter", "diet", "dietary"],
    "item_id": ["item_id", "itemId"],
    "items": ["items"],
    "delivery_address": ["delivery_address", "address"],
    "promo_code": ["promo_code", "promoCode", "coupon"],
    "payment_type": ["payment_type", "paymentType"],
}

CITY_COORDS: dict[str, tuple[float, float]] = {
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "indiranagar": (12.9784, 77.6408),
    "koramangala": (12.9352, 77.6245),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
}


_DISH_WORDS = (
    "pizza", "biryani", "burger", "thali", "pasta", "sushi", "chinese", "indian",
    "salad", "sandwich", "dosa", "idli", "noodles", "shawarma", "momos", "coffee",
    "breakfast", "dessert", "rolls", "paneer", "chicken",
)


def _eta_minutes(text: str) -> Optional[int]:
    parts = text.lower().replace("–", " ").replace("-", " ").split()
    for index, part in enumerate(parts):
        if part.isdigit() and index + 1 < len(parts) and parts[index + 1].startswith("min"):
            return int(part)
    return None


def zomato_keyword(query: str) -> str:
    """Turn a dining prompt into the short keyword Zomato's search tool expects."""
    text = query.lower()
    dishes = [word for word in _DISH_WORDS if word in text]
    if dishes:
        base = " and ".join(dishes[:3])
    elif "protein" in text or "keto" in text:
        base = "high protein"
    elif "vegan" in text:
        base = "healthy"
    elif "dinner" in text:
        base = "dinner"
    elif "breakfast" in text:
        base = "breakfast"
    else:
        base = "lunch"
    eta = _eta_minutes(text)
    if eta:
        return f"{base} from restaurants under {eta} minutes"
    return base


def _coords_for(location: str) -> Optional[tuple[float, float]]:
    key = location.strip().lower()
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    for name, coords in CITY_COORDS.items():
        if name in key:
            return coords
    return None


def _first_number(value: Any, default: float = 0) -> float:
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        digits = "".join(ch if (ch.isdigit() or ch == ".") else " " for ch in value).split()
        if digits:
            try:
                return float(digits[0])
            except ValueError:
                return default
    if isinstance(value, dict):
        for key in ("aggregate_rating", "rating", "value", "amount", "price"):
            if key in value:
                return _first_number(value[key], default)
    return default


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(_as_text(item) for item in value if item)
    if isinstance(value, dict):
        for key in ("address", "locality", "name", "city", "label"):
            if value.get(key):
                return _as_text(value[key])
        return ""
    return str(value)


def _parse_tool_payload(result: Any) -> Any:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        structured = structured["result"]
    if structured:
        return structured
    content = getattr(result, "content", None) or []
    if not content:
        return result
    block = content[0]
    text = getattr(block, "text", None)
    if text is None and isinstance(block, dict):
        text = block.get("text")
    if not isinstance(text, str):
        return block
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {"text": text}


def normalize_restaurants(payload: Any, fallback_location: str = "") -> list[dict[str, Any]]:
    """Flatten whatever the Zomato search tool returns into FlavorPilot cards."""
    if isinstance(payload, dict) and "text" in payload and len(payload) == 1:
        return []

    candidates: list[Any] = []
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        for key in ("results", "restaurants", "data", "items", "outlets"):
            if isinstance(payload.get(key), list):
                candidates = payload[key]
                break
        else:
            candidates = [payload]

    restaurants: list[dict[str, Any]] = []
    for raw in candidates:
        item = raw.get("restaurant", raw) if isinstance(raw, dict) else None
        if not isinstance(item, dict):
            continue
        name = _as_text(item.get("name") or item.get("restaurant_name") or item.get("res_name"))
        if not name:
            continue
        restaurant_id = _as_text(
            item.get("res_id") or item.get("restaurant_id") or item.get("id") or item.get("restaurantId")
        ) or name
        tags = item.get("tags") or item.get("highlights") or []
        if isinstance(tags, str):
            tags = [part.strip() for part in tags.split(",") if part.strip()]
        elif not isinstance(tags, list):
            tags = []
        offer = _as_text(item.get("res_offer") or item.get("offer"))
        if offer:
            tags = [offer, *tags]
        distance = item.get("distance")
        if distance:
            tags.append(f"{distance} km")
        location = _as_text(item.get("location") or item.get("locality") or item.get("address"))
        if not location and distance:
            location = f"{distance} km away"
        restaurants.append({
            "restaurant_id": restaurant_id,
            "name": name,
            "cuisine": _as_text(item.get("cuisine") or item.get("cuisines") or item.get("category")) or "Delivery",
            "location": location or fallback_location,
            "rating": _first_number(item.get("rating") or item.get("aggregate_rating") or item.get("user_rating")),
            "eta_mins": int(_first_number(item.get("eta_mins") or item.get("eta") or item.get("delivery_time") or 30)),
            "delivery_fee_inr": _first_number(item.get("delivery_fee_inr") or item.get("delivery_fee") or item.get("deliveryFee")),
            "tags": [str(tag) for tag in tags if tag][:8],
            "image_url": _as_text(item.get("res_image") or item.get("image_url") or item.get("image")) or None,
            "offer": offer or None,
            "menu_items": _dishes_from_search(item.get("items")),
        })
    return restaurants


def normalize_menu(payload: Any, restaurant_id: str) -> dict[str, Any]:
    """Flatten a Zomato menu payload into categories of priced items."""
    raw_items: list[Any] = []
    categories_in: list[Any] = []
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]
        if isinstance(data.get("partial_menu"), list):
            raw_items = data["partial_menu"]
        elif isinstance(data.get("item_mappings"), list):
            raw_items = data["item_mappings"]
    elif isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        for key in ("categories", "menu", "menus", "sections"):
            if isinstance(payload.get(key), list):
                categories_in = payload[key]
                break
        if not categories_in:
            for key in ("items", "menu_items", "dishes", "data"):
                if isinstance(payload.get(key), list):
                    raw_items = payload[key]
                    break

    categories: list[dict[str, Any]] = []
    if categories_in:
        for category in categories_in:
            if not isinstance(category, dict):
                continue
            name = _as_text(category.get("name") or category.get("title") or category.get("category")) or "Menu"
            source = category.get("items") or category.get("dishes") or category.get("menu_items") or []
            items = [_menu_item(entry) for entry in source if isinstance(entry, dict)]
            items = [item for item in items if item]
            if items:
                categories.append({"name": name, "items": items})
    else:
        items = [_menu_item(entry) for entry in raw_items if isinstance(entry, dict)]
        items = [item for item in items if item]
        if items:
            categories.append({"name": "Menu", "items": items})

    return {"restaurant_id": restaurant_id, "categories": categories}


def flatten_menu_items(menu: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for category in menu.get("categories", []):
        for item in category.get("items", []):
            items.append({
                "item_id": str(item.get("item_id", "")),
                "name": item.get("name", "Item"),
                "price_inr": float(item.get("price_inr") or 0),
                "tags": item.get("tags") or [],
                "detail": item.get("detail") or category.get("name") or "",
            })
    return items


def _dishes_from_search(raw_items: Any) -> list[dict[str, Any]]:
    """Dishes embedded in a get_restaurants_for_keyword result."""
    if not isinstance(raw_items, list):
        return []
    dishes: list[dict[str, Any]] = []
    for entry in raw_items:
        if not isinstance(entry, dict) or entry.get("name") in (None, "NOT_RETRIEVED"):
            continue
        item = _menu_item(entry)
        if item:
            dishes.append(item)
    return dishes


def _menu_item(entry: dict[str, Any]) -> Optional[dict[str, Any]]:
    item = entry.get("item", entry) if isinstance(entry.get("item"), dict) else entry
    name = _as_text(item.get("name") or item.get("item_name") or item.get("title"))
    if not name:
        return None
    tags = item.get("item_tags") or item.get("tags") or item.get("dietary_tags") or []
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split(",") if part.strip()]
    elif not isinstance(tags, list):
        tags = []
    if item.get("is_veg") is True:
        tags = ["veg", *tags]
    elif item.get("is_veg") is False:
        tags = ["non-veg", *tags]
    detail = _as_text(item.get("description") or item.get("detail") or item.get("subtitle"))
    return {
        "item_id": _as_text(item.get("variant_id") or item.get("item_id") or item.get("catalogue_id") or item.get("id")) or name,
        "name": name,
        "price_inr": _first_number(item.get("min_price") or item.get("price_inr") or item.get("discounted_price") or item.get("price") or item.get("cost")),
        "tags": [str(tag) for tag in tags if tag][:6],
        "detail": detail,
        "protein_g": item.get("protein_g"),
        "carbs_g": item.get("carbs_g"),
        "fat_g": item.get("fat_g"),
    }


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
        self._tools: dict[str, Any] = {}
        self._address_id: Optional[str] = None
        self._menus: dict[str, dict[str, Any]] = {}
    
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
            
            # Initialize session and cache the live tool list.
            await self._session.initialize()
            listed = await self._session.list_tools()
            self._tools = {tool.name: tool for tool in listed.tools}
            
            self._connected = True
            logger.info(
                "Connected to Zomato MCP (%s). Tools: %s",
                self.server_url,
                ", ".join(self._tools) or "(none)",
            )
            
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
    
    def _resolve_tool(self, logical_name: str) -> str:
        """Pick the live tool name for a FlavorPilot operation."""
        for candidate in TOOL_ALIASES.get(logical_name, [logical_name]):
            if candidate in self._tools:
                return candidate
        for available in self._tools:
            if logical_name in available.replace(".", "_"):
                return available
        available = ", ".join(sorted(self._tools)) or "none"
        raise ZomatoMCPToolError(
            f"Zomato MCP has no '{logical_name}' tool. Available tools: {available}"
        )

    def _build_arguments(self, tool_name: str, values: dict[str, Any]) -> dict[str, Any]:
        """Keep only arguments the live tool schema accepts, translating our names."""
        tool = self._tools.get(tool_name)
        schema = getattr(tool, "inputSchema", None) or {}
        properties = schema.get("properties") or {}
        if not properties:
            return {key: value for key, value in values.items() if value is not None}

        arguments: dict[str, Any] = {}
        for key, value in values.items():
            if value is None:
                continue
            for candidate in ARGUMENT_ALIASES.get(key, [key]):
                if candidate in properties:
                    prop = properties[candidate] or {}
                    if prop.get("type") == "integer" and not isinstance(value, bool):
                        try:
                            value = int(value)
                        except (TypeError, ValueError):
                            pass
                    arguments[candidate] = value
                    break

        location = values.get("location")
        coords = _coords_for(location) if isinstance(location, str) else None
        if coords:
            lat, lng = coords
            for candidate in ARGUMENT_ALIASES["latitude"]:
                if candidate in properties and candidate not in arguments:
                    arguments[candidate] = lat
                    break
            for candidate in ARGUMENT_ALIASES["longitude"]:
                if candidate in properties and candidate not in arguments:
                    arguments[candidate] = lng
                    break

        # Tools that only accept a free-text query still need the user's words.
        text_keys = [key for key in ("query", "q", "prompt", "text") if key in properties]
        if text_keys and text_keys[0] not in arguments and values.get("query"):
            arguments[text_keys[0]] = values["query"]
        return arguments

    async def _call_tool(self, logical_name: str, arguments: dict[str, Any]) -> Any:
        """Call a live Zomato MCP tool."""
        if not self._connected or not self._session:
            raise ZomatoMCPConnectionError("MCP client not connected")

        tool_name = self._resolve_tool(logical_name)
        payload = self._build_arguments(tool_name, arguments)

        try:
            logger.info("Calling Zomato tool '%s' with %s", tool_name, payload)
            result = await self._session.call_tool(tool_name, payload)
            if getattr(result, "isError", False):
                message = _parse_tool_payload(result)
                raise ZomatoMCPToolError(f"{tool_name} failed: {message}")
            return _parse_tool_payload(result)
        except ZomatoMCPToolError:
            raise
        except Exception as e:
            logger.error("Tool '%s' execution failed: %s", tool_name, e)
            raise ZomatoMCPToolError(f"Tool execution failed: {e}") from e
    
    # ===== Zomato MCP Tool Methods =====
    
    async def search_restaurants(
        self,
        query: str,
        location: str,
        cuisine: Optional[str] = None,
        max_delivery_mins: Optional[int] = None,
        budget_cap_inr: Optional[float] = None,
        keyword: Optional[str] = None,
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
        keyword = keyword.strip() if keyword and keyword.strip() else zomato_keyword(query)
        arguments = {
            "query": keyword,
            "location": location,
            "page_size": 8,
        }
        
        if cuisine:
            arguments["cuisine"] = cuisine
        if max_delivery_mins:
            arguments["max_delivery_mins"] = max_delivery_mins
        if budget_cap_inr and budget_cap_inr <= 800:
            arguments["filter"] = {"max_price": budget_cap_inr}
        address = await self._resolve_address(location)
        arguments["address_id"] = address["address_id"]
        
        payload = await self._call_tool("search_restaurants", arguments)
        restaurants = normalize_restaurants(payload, fallback_location=location)
        if not restaurants and keyword != "lunch":
            arguments["query"] = "lunch"
            arguments.pop("filter", None)
            payload = await self._call_tool("search_restaurants", arguments)
            restaurants = normalize_restaurants(payload, fallback_location=location)
        if not restaurants and isinstance(payload, dict) and payload.get("text"):
            raise ZomatoMCPToolError(str(payload["text"]))
        for restaurant in restaurants:
            dishes = restaurant.get("menu_items") or []
            if dishes:
                self._menus[str(restaurant["restaurant_id"])] = {
                    "restaurant_id": restaurant["restaurant_id"],
                    "categories": [{"name": "Matching dishes", "items": dishes}],
                }
        return restaurants
    
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

        cached = self._menus.get(str(restaurant_id))
        if cached:
            return cached

        if not self._address_id:
            address = await self._resolve_address(None)
            arguments["address_id"] = address["address_id"]
        else:
            arguments["address_id"] = self._address_id
        
        payload = await self._call_tool("get_menu", arguments)
        menu = normalize_menu(payload, restaurant_id)
        self._menus[str(restaurant_id)] = menu
        return menu

    async def _resolve_address(self, location: Optional[str]) -> dict[str, Any]:
        """Pick a saved Zomato address. Search cannot run without one."""
        payload = await self._call_tool("get_saved_addresses", {})
        addresses = payload.get("addresses") if isinstance(payload, dict) else None
        if not addresses:
            raise ZomatoMCPToolError(
                "This Zomato account has no saved delivery address. Add one in the Zomato app, then search again."
            )
        wanted = str(settings.zomato_address_id)
        chosen = next((address for address in addresses if str(address.get("address_id")) == wanted), None)
        if chosen is None:
            raise ZomatoMCPToolError(
                f"Saved Zomato address {wanted} was not on this account."
            )
        self._address_id = wanted
        return chosen
    
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
        return await self._call_tool("get_item_customizations", arguments)
    
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
        return await self._call_tool("apply_promo_code", arguments)
    
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
            "restaurant_id": delivery_address.get("restaurant_id") if isinstance(delivery_address, dict) else None,
            "address_id": delivery_address.get("address_id") if isinstance(delivery_address, dict) else None,
            "promo_code": delivery_address.get("promo_code") if isinstance(delivery_address, dict) else None,
        }
        return await self._call_tool("create_cart", arguments)


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
