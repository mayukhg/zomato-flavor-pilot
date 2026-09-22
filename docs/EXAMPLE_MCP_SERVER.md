# Example Zomato MCP Server Implementation

This is a reference implementation of a Zomato MCP server that wraps the Zomato REST API.

**Note**: This is a starting template. You'll need a real Zomato API key to make it work.

---

## Setup

```bash
mkdir zomato-mcp-server
cd zomato-mcp-server
npm init -y
npm install @modelcontextprotocol/sdk axios dotenv
```

Create `.env`:
```env
ZOMATO_API_KEY=your_actual_zomato_api_key_here
ZOMATO_BASE_URL=https://developers.zomato.com/api/v2.1
```

---

## Implementation

### index.js

```javascript
#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const ZOMATO_API_KEY = process.env.ZOMATO_API_KEY;
const ZOMATO_BASE_URL = process.env.ZOMATO_BASE_URL || 'https://developers.zomato.com/api/v2.1';

if (!ZOMATO_API_KEY) {
  console.error('Error: ZOMATO_API_KEY not set in environment');
  process.exit(1);
}

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

// Helper: Make authenticated Zomato API request
async function zomatoRequest(endpoint, params = {}) {
  try {
    const response = await axios.get(`${ZOMATO_BASE_URL}${endpoint}`, {
      headers: { 'user-key': ZOMATO_API_KEY },
      params,
    });
    return response.data;
  } catch (error) {
    throw new Error(`Zomato API error: ${error.response?.data?.message || error.message}`);
  }
}

// Tool: Search Restaurants
async function searchRestaurants({ query, location, cuisine, max_delivery_mins, budget_cap_inr }) {
  // Get location coordinates (simplified - use geocoding service in production)
  const geoData = await zomatoRequest('/geocode', {
    lat: 12.9716,  // Bangalore - replace with actual geocoding
    lon: 77.5946,
  });

  const searchParams = {
    entity_id: geoData.location.entity_id,
    entity_type: 'city',
    q: query,
    sort: 'rating',
    order: 'desc',
  };

  if (cuisine) searchParams.cuisines = cuisine;

  const data = await zomatoRequest('/search', searchParams);

  return data.restaurants
    .map(r => ({
      restaurant_id: r.restaurant.id.toString(),
      name: r.restaurant.name,
      cuisine: r.restaurant.cuisines,
      location: r.restaurant.location.address,
      rating: parseFloat(r.restaurant.user_rating.aggregate_rating),
      price_for_two: r.restaurant.average_cost_for_two,
      delivery_available: r.restaurant.has_online_delivery === 1,
      eta_mins: 30, // Zomato API doesn't provide this - estimate
      delivery_fee_inr: 0, // Not available in public API
      tags: [],
    }))
    .filter(r => !budget_cap_inr || r.price_for_two <= budget_cap_inr * 2)
    .slice(0, 10);
}

// Tool: Get Menu
async function getMenu({ restaurant_id, dietary_filter }) {
  const data = await zomatoRequest('/dailymenu', { res_id: restaurant_id });

  const items = data.daily_menus.flatMap(menu =>
    menu.daily_menu.dishes.map(dish => ({
      item_id: dish.dish.dish_id.toString(),
      name: dish.dish.name,
      price_inr: parseFloat(dish.dish.price) || 0,
      // Nutritional info not available in public API - would need separate source
      protein_g: 0,
      carbs_g: 0,
      fat_g: 0,
      tags: dietary_filter ? [dietary_filter] : [],
    }))
  );

  return {
    restaurant_id,
    categories: [
      {
        name: 'Menu Items',
        items,
      },
    ],
  };
}

// Tool: Get Item Customizations
async function getItemCustomizations({ item_id }) {
  // Zomato public API doesn't provide customization details
  // Return generic options
  return {
    item_id,
    customizations: [
      {
        group: 'portion_size',
        options: [
          { id: 'regular', name: 'Regular', price_delta: 0 },
          { id: 'large', name: 'Large', price_delta: 50 },
        ],
      },
      {
        group: 'spice_level',
        options: [
          { id: 'mild', name: 'Mild' },
          { id: 'medium', name: 'Medium' },
          { id: 'spicy', name: 'Spicy' },
        ],
      },
    ],
  };
}

// Tool: Apply Promo Code
async function applyPromoCode({ cart_id, promo_code }) {
  // Zomato public API doesn't support promo code validation
  // Would need Zomato ordering API access
  return {
    cart_id,
    promo_code,
    discount_inr: promo_code === 'FLAT200' ? 200 : 0,
    status: promo_code === 'FLAT200' ? 'applied' : 'invalid',
  };
}

// Tool: Build Cart
async function buildCart({ items, delivery_address }) {
  // Zomato public API doesn't support cart creation
  // Would need Zomato ordering API access
  const cart_id = `cart_${Date.now()}`;
  const total = items.reduce((sum, item) => sum + (item.price || 0) * (item.quantity || 1), 0);

  return {
    cart_id,
    items,
    delivery_address,
    total_inr: total,
    delivery_fee_inr: 40,
    taxes_inr: total * 0.05,
    grand_total_inr: total + 40 + total * 0.05,
  };
}

// Handle tool calls
server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;

  let result;
  try {
    switch (name) {
      case 'zomato.search_restaurants':
        result = await searchRestaurants(args);
        break;
      case 'zomato.get_menu':
        result = await getMenu(args);
        break;
      case 'zomato.get_item_customizations':
        result = await getItemCustomizations(args);
        break;
      case 'zomato.apply_promo_code':
        result = await applyPromoCode(args);
        break;
      case 'zomato.build_cart':
        result = await buildCart(args);
        break;
      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ error: error.message }),
        },
      ],
      isError: true,
    };
  }
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
            query: { type: 'string', description: 'Search query (e.g., "pizza", "vegan")' },
            location: { type: 'string', description: 'Location (e.g., "Koramangala, Bangalore")' },
            cuisine: { type: 'string', description: 'Cuisine filter (optional)' },
            max_delivery_mins: { type: 'number', description: 'Max delivery time in minutes (optional)' },
            budget_cap_inr: { type: 'number', description: 'Maximum budget in INR (optional)' },
          },
          required: ['query', 'location'],
        },
      },
      {
        name: 'zomato.get_menu',
        description: 'Get menu items for a restaurant',
        inputSchema: {
          type: 'object',
          properties: {
            restaurant_id: { type: 'string', description: 'Restaurant ID from search results' },
            dietary_filter: { type: 'string', description: 'Dietary filter: vegan, keto, halal, nut_free (optional)' },
          },
          required: ['restaurant_id'],
        },
      },
      {
        name: 'zomato.get_item_customizations',
        description: 'Get customization options for a menu item',
        inputSchema: {
          type: 'object',
          properties: {
            item_id: { type: 'string', description: 'Menu item ID' },
          },
          required: ['item_id'],
        },
      },
      {
        name: 'zomato.apply_promo_code',
        description: 'Apply a promo code to the cart',
        inputSchema: {
          type: 'object',
          properties: {
            cart_id: { type: 'string', description: 'Cart ID' },
            promo_code: { type: 'string', description: 'Promo code to apply' },
          },
          required: ['cart_id', 'promo_code'],
        },
      },
      {
        name: 'zomato.build_cart',
        description: 'Build a cart with selected items',
        inputSchema: {
          type: 'object',
          properties: {
            items: {
              type: 'array',
              description: 'Array of items to add to cart',
              items: {
                type: 'object',
                properties: {
                  item_id: { type: 'string' },
                  quantity: { type: 'number' },
                  customizations: { type: 'array', items: { type: 'string' } },
                },
              },
            },
            delivery_address: {
              type: 'object',
              description: 'Delivery address',
              properties: {
                street: { type: 'string' },
                city: { type: 'string' },
                pincode: { type: 'string' },
              },
            },
          },
          required: ['items', 'delivery_address'],
        },
      },
    ],
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Zomato MCP server running on stdio');
}

main().catch(console.error);
```

### package.json

```json
{
  "name": "zomato-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "main": "index.js",
  "bin": {
    "zomato-mcp-server": "./index.js"
  },
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "axios": "^1.6.0",
    "dotenv": "^16.0.0"
  }
}
```

---

## Usage

### Test Locally

```bash
# Make executable
chmod +x index.js

# Run server
./index.js

# In another terminal, test with MCP inspector
npx @modelcontextprotocol/inspector ./index.js
```

### Use with FlavorPilot

Edit `/workspace/.env`:

```env
USE_MOCK_MCP=false
ZOMATO_MCP_TRANSPORT=stdio
ZOMATO_MCP_STDIO_CMD=/path/to/zomato-mcp-server/index.js
```

Restart FlavorPilot:

```bash
cd /workspace
./stop.sh
./start.sh
```

---

## Limitations

This example implementation has limitations due to Zomato's public API constraints:

1. **Menu Details**: Limited nutritional information
2. **Customizations**: Generic options only
3. **Promo Codes**: Cannot validate real codes
4. **Cart Creation**: No real cart API access
5. **Delivery ETA**: Estimated, not real-time

For production, you would need:
- Zomato Partner API access (not public)
- Or official Zomato MCP server from Zomato
- Additional data sources for nutritional info

---

## Production Enhancements

Add these for production use:

1. **Caching**: Cache restaurant data
2. **Rate Limiting**: Respect Zomato API limits
3. **Error Handling**: Retry logic with exponential backoff
4. **Logging**: Structured logging for debugging
5. **Authentication**: Secure API key handling
6. **Monitoring**: Track API usage and errors

---

**See Also**:
- `docs/ZOMATO_MCP_CONNECTION.md` - Full connection guide
- Zomato API docs: https://developers.zomato.com/documentation
- MCP Protocol: https://modelcontextprotocol.io/
