"""Live Zomato MCP connection status for the FlavorPilot UI."""
import time

from fastapi import APIRouter

from backend.app.config import settings
from backend.app.mcp import ZomatoMCPClient

router = APIRouter()

_cache: dict = {"at": 0.0, "payload": None}
_CACHE_SECONDS = 60


@router.get("/status")
async def mcp_status():
    """Connect to the official Zomato MCP server and report the live tool list."""
    now = time.time()
    cached = _cache["payload"]
    if cached and cached.get("connected") and now - _cache["at"] < _CACHE_SECONDS:
        return cached

    client = ZomatoMCPClient()
    try:
        await client.connect()
        payload = {
            "connected": True,
            "server": settings.zomato_mcp_server_url,
            "tools": sorted(client._tools),
        }
    except Exception as exc:
        payload = {
            "connected": False,
            "server": settings.zomato_mcp_server_url,
            "tools": [],
            "detail": str(exc),
        }
    finally:
        await client.disconnect()

    if payload["connected"]:
        _cache["at"] = now
        _cache["payload"] = payload
    return payload
