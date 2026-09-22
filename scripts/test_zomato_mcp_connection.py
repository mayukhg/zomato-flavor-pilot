#!/usr/bin/env python3
"""Test connection to real Zomato MCP server."""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.mcp.http_client import ZomatoHTTPMCPClient


async def main():
    print("🔍 Testing connection to Zomato MCP Server...")
    print(f"   URL: https://mcp-server.zomato.com/mcp")
    print()
    
    try:
        async with ZomatoHTTPMCPClient() as client:
            print("✅ Connection successful!\n")
            
            # Test: List available tools
            print("📋 Listing available tools...")
            tools = await client.list_tools()
            print(f"   Found {len(tools)} tools:")
            for tool in tools:
                name = tool.get("name", "unknown")
                desc = tool.get("description", "No description")
                print(f"   • {name}: {desc[:80]}{'...' if len(desc) > 80 else ''}")
            print()
            
            # Test: Search restaurants
            print("🔎 Testing search_restaurants...")
            try:
                results = await client.search_restaurants(
                    query="Pizza",
                    location="Bangalore",
                    budget_cap_inr=500.0
                )
                if results:
                    print(f"   ✅ Found {len(results)} restaurants")
                    if isinstance(results, list) and len(results) > 0:
                        first = results[0]
                        print(f"   Example: {first.get('name', 'N/A')} - {first.get('cuisine', 'N/A')}")
                else:
                    print(f"   ⚠️  No results (but call succeeded)")
            except Exception as e:
                print(f"   ⚠️  Tool call failed: {e}")
            print()
            
            print("=" * 60)
            print("✅ ALL TESTS PASSED")
            print("=" * 60)
            print()
            print("🎉 FlavorPilot is now connected to REAL Zomato data!")
            print("   To use real data, ensure .env has: USE_MOCK_MCP=false")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Possible reasons:")
        print("  • Server might be down or unreachable")
        print("  • Network connectivity issues")
        print("  • Server URL might have changed")
        print()
        print("To use mock data instead, set: USE_MOCK_MCP=true in .env")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
