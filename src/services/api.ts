/**
 * FlavorPilot API Client
 * 
 * Typed API client for backend communication.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// ===== Types =====

export interface SearchRequest {
  query: string;
  location: string;
  cuisine?: string;
  max_delivery_mins?: number;
  budget_cap_inr?: number;
  group_size?: number;
  dietary_constraints?: string[];
}

export interface RestaurantResult {
  restaurant_id: string;
  name: string;
  cuisine: string;
  location: string;
  rating: number;
  eta_mins: number;
  delivery_fee_inr: number;
  tags: string[];
  image_url?: string | null;
}

export interface MenuItemResult {
  item_id: string;
  name: string;
  price_inr: number;
  tags: string[];
  detail: string;
}

export interface SearchResponse {
  restaurants: RestaurantResult[];
  menu_items: MenuItemResult[];
  session_id?: string;
  execution_time_ms: number;
  model_used: string;
}

export interface AgentStep {
  agent_type: 'lead' | 'worker';
  worker_id?: string;
  step_number: number;
  tool_name: string;
  tool_arguments: Record<string, any>;
  tool_result: Record<string, any>;
  status: 'success' | 'error' | 'pending';
  execution_time_ms: number;
  model_used: string;
  cost_usd: number;
}

export interface AgentTrajectoryResponse {
  session_id: string;
  user_prompt: string;
  steps: AgentStep[];
  total_execution_time_ms: number;
  total_cost_usd: number;
  status: 'completed' | 'error' | 'in_progress';
}

export interface CartItem {
  item_id: string;
  name: string;
  quantity: number;
  price_inr: number;
  customizations?: Record<string, any>;
  tags: string[];
}

export interface DeliveryAddress {
  street: string;
  area: string;
  city: string;
  pincode: string;
  landmark?: string;
}

export interface BuildCartRequest {
  session_id: string;
  restaurant_id: string;
  items: CartItem[];
  delivery_address: DeliveryAddress;
  promo_code?: string;
}

export interface CartResponse {
  cart_id: string;
  session_id: string;
  restaurant_id: string;
  restaurant_name: string;
  items: CartItem[];
  subtotal_inr: number;
  discount_inr: number;
  delivery_fee_inr: number;
  platform_fee_inr: number;
  total_inr: number;
  promo_code?: string;
  status: 'staged' | 'approved' | 'rejected' | 'placed';
  created_at: string;
}

export interface ApproveCartRequest {
  cart_id: string;
  allergen_confirmed: boolean;
}

export interface ApproveCartResponse {
  cart_id: string;
  status: 'approved' | 'rejected';
  message: string;
  order_token?: string;
}

export interface EvalSummaryResponse {
  total_cases: number;
  passed: number;
  failed: number;
  avg_groundedness: number;
  avg_safety: number;
  avg_execution_time_ms: number;
  total_cost_usd: number;
}

// ===== API Client =====

class FlavorPilotAPI {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      const detail = typeof error.detail === 'string' ? error.detail : error.message;
      throw new Error(detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  // ===== Search =====

  async searchRestaurants(request: SearchRequest): Promise<SearchResponse> {
    return this.request<SearchResponse>('/search', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // ===== Agent Trajectory =====

  async getAgentTrajectory(sessionId: string): Promise<AgentTrajectoryResponse> {
    return this.request<AgentTrajectoryResponse>(`/agent/trajectory/${sessionId}`);
  }

  // ===== Cart =====

  async buildCart(request: BuildCartRequest): Promise<CartResponse> {
    return this.request<CartResponse>('/cart/build', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async approveCart(request: ApproveCartRequest): Promise<ApproveCartResponse> {
    return this.request<ApproveCartResponse>('/cart/approve', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getCart(cartId: string): Promise<CartResponse> {
    return this.request<CartResponse>(`/cart/${cartId}`);
  }

  // ===== Evaluations =====

  async getEvalSummary(): Promise<EvalSummaryResponse> {
    return this.request<EvalSummaryResponse>('/evals/summary');
  }

  // ===== Health =====

  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }

  async mcpStatus(): Promise<{ connected: boolean; server: string; tools: string[]; detail?: string }> {
    return this.request('/mcp/status');
  }
}

export const api = new FlavorPilotAPI();
