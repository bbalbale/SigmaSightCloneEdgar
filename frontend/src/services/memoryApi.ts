/**
 * Memory API Service
 *
 * Provides CRUD operations for user memories (AI personalization data).
 * Memories store user preferences, corrections, and context that persists
 * across conversations to personalize the AI assistant's responses.
 */

import { apiClient } from './apiClient';

// Types
export interface Memory {
  id: string;
  scope: 'user' | 'portfolio';
  content: string;
  tags: Record<string, any>;
  created_at: string | null;
}

export interface MemoryListResponse {
  memories: Memory[];
  total: number;
  limit: number;
}

export interface MemoryCountResponse {
  count: number;
  max_allowed: number;
}

export interface CreateMemoryParams {
  content: string;
  scope?: 'user' | 'portfolio';
  portfolio_id?: string;
  tags?: Record<string, any>;
}

// API functions
const memoryApi = {
  /**
   * List all memories for the current user
   * @param scope - Optional filter by scope ('user' or 'portfolio')
   * @param portfolioId - Optional filter by portfolio ID
   * @param limit - Maximum number of memories to return (default: 50)
   */
  async listMemories(
    scope?: 'user' | 'portfolio',
    portfolioId?: string,
    limit: number = 50
  ): Promise<MemoryListResponse> {
    const params = new URLSearchParams();
    if (scope) params.append('scope', scope);
    if (portfolioId) params.append('portfolio_id', portfolioId);
    params.append('limit', limit.toString());

    const queryString = params.toString();
    const endpoint = `/api/v1/chat/memories${queryString ? `?${queryString}` : ''}`;

    return apiClient.get<MemoryListResponse>(endpoint);
  },

  /**
   * Create a new memory
   * @param params - Memory creation parameters
   */
  async createMemory(params: CreateMemoryParams): Promise<Memory> {
    return apiClient.post<Memory>('/api/v1/chat/memories', params);
  },

  /**
   * Delete a specific memory by ID
   * @param memoryId - The memory UUID to delete
   */
  async deleteMemory(memoryId: string): Promise<void> {
    await apiClient.delete(`/api/v1/chat/memories/${memoryId}`);
  },

  /**
   * Delete all memories for the current user
   * @returns Number of memories deleted
   */
  async deleteAllMemories(): Promise<{ deleted: number }> {
    return apiClient.delete('/api/v1/chat/memories');
  },

  /**
   * Get the count of memories for the current user
   */
  async getMemoryCount(): Promise<MemoryCountResponse> {
    return apiClient.get<MemoryCountResponse>('/api/v1/chat/memories/count');
  },
};

export default memoryApi;
