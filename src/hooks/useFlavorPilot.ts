/**
 * FlavorPilot React Query Hooks
 * 
 * Custom hooks for API interactions with caching and state management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  api,
  SearchRequest,
  SearchResponse,
  AgentTrajectoryResponse,
  BuildCartRequest,
  CartResponse,
  ApproveCartRequest,
  ApproveCartResponse,
  EvalSummaryResponse,
} from '@/services/api';

// ===== Query Keys =====

export const queryKeys = {
  search: (request: SearchRequest) => ['search', request] as const,
  trajectory: (sessionId: string) => ['trajectory', sessionId] as const,
  cart: (cartId: string) => ['cart', cartId] as const,
  evalSummary: () => ['evalSummary'] as const,
  health: () => ['health'] as const,
};

// ===== Search Hooks =====

export function useSearchRestaurants() {
  return useMutation<SearchResponse, Error, SearchRequest>({
    mutationFn: (request) => api.searchRestaurants(request),
  });
}

// ===== Agent Trajectory Hooks =====

export function useAgentTrajectory(sessionId: string | null) {
  return useQuery<AgentTrajectoryResponse, Error>({
    queryKey: queryKeys.trajectory(sessionId || ''),
    queryFn: () => api.getAgentTrajectory(sessionId!),
    enabled: !!sessionId,
    refetchInterval: (query) => {
      // Refetch while in progress
      const status = query.state.data?.status;
      return status === 'in_progress' ? 2000 : false;
    },
  });
}

// ===== Cart Hooks =====

export function useBuildCart() {
  const queryClient = useQueryClient();
  
  return useMutation<CartResponse, Error, BuildCartRequest>({
    mutationFn: (request) => api.buildCart(request),
    onSuccess: (data) => {
      // Cache the newly built cart
      queryClient.setQueryData(queryKeys.cart(data.cart_id), data);
    },
  });
}

export function useApproveCart() {
  const queryClient = useQueryClient();
  
  return useMutation<ApproveCartResponse, Error, ApproveCartRequest>({
    mutationFn: (request) => api.approveCart(request),
    onSuccess: (_, variables) => {
      // Invalidate cart cache to refetch updated status
      queryClient.invalidateQueries({ queryKey: queryKeys.cart(variables.cart_id) });
    },
  });
}

export function useCart(cartId: string | null) {
  return useQuery<CartResponse, Error>({
    queryKey: queryKeys.cart(cartId || ''),
    queryFn: () => api.getCart(cartId!),
    enabled: !!cartId,
  });
}

// ===== Evaluation Hooks =====

export function useEvalSummary() {
  return useQuery<EvalSummaryResponse, Error>({
    queryKey: queryKeys.evalSummary(),
    queryFn: () => api.getEvalSummary(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

// ===== Health Check =====

export function useHealthCheck() {
  return useQuery<{ status: string }, Error>({
    queryKey: queryKeys.health(),
    queryFn: () => api.healthCheck(),
    refetchInterval: 60000, // Refetch every minute
    retry: 3,
  });
}

// ===== Combined FlavorPilot Hook =====

export function useFlavorPilot() {
  const searchRestaurants = useSearchRestaurants();
  const buildCart = useBuildCart();
  const approveCart = useApproveCart();
  
  return {
    // Search
    searchRestaurants: searchRestaurants.mutate,
    searchRestaurantsAsync: searchRestaurants.mutateAsync,
    isSearching: searchRestaurants.isPending,
    searchError: searchRestaurants.error,
    searchData: searchRestaurants.data,
    
    // Cart
    buildCart: buildCart.mutate,
    buildCartAsync: buildCart.mutateAsync,
    isBuildingCart: buildCart.isPending,
    cartBuildError: buildCart.error,
    cartData: buildCart.data,
    
    // Approval
    approveCart: approveCart.mutate,
    approveCartAsync: approveCart.mutateAsync,
    isApprovingCart: approveCart.isPending,
    approvalError: approveCart.error,
    approvalData: approveCart.data,
  };
}
