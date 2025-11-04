/**
 * Position Management Service
 *
 * Provides CRUD operations for position management covering all 9 backend endpoints.
 *
 * Backend Endpoints (Day 1-6 Implementation):
 * 1. POST /api/v1/positions - Create position
 * 2. GET /api/v1/positions/{id} - Get single position
 * 3. PUT /api/v1/positions/{id} - Update position
 * 4. GET /api/v1/positions/validate-symbol/{symbol} - Validate symbol
 * 5. GET /api/v1/positions/check-duplicate - Check for duplicates
 * 6. POST /api/v1/positions/bulk - Bulk create positions
 * 7. DELETE /api/v1/positions/{id} - Soft delete position
 * 8. DELETE /api/v1/positions/bulk - Bulk soft delete
 * 9. DELETE /api/v1/positions/{id}/hard - Hard delete (Reverse Addition)
 *
 * Related Files:
 * - Backend: backend/app/api/v1/positions.py (position endpoints)
 * - Backend: backend/app/services/position_service.py (position business logic)
 * - Backend: backend/scripts/test_position_endpoints.py (integration tests)
 */

import { apiClient } from './apiClient';
import { authManager } from './authManager';
import { REQUEST_CONFIGS } from '@/config/api';

// ===== Type Definitions =====

/**
 * Position types following backend PositionType enum
 */
export type PositionType = 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP';

/**
 * Investment classes following backend Position model
 */
export type InvestmentClass = 'PUBLIC' | 'OPTIONS' | 'PRIVATE';

/**
 * Position data structure matching backend Position model
 */
export interface Position {
  id: string;
  portfolio_id: string;
  symbol: string;
  position_type: PositionType;
  investment_class: InvestmentClass;
  quantity: number;
  avg_cost: number;
  entry_price: number;
  entry_date?: string;
  exit_date?: string;
  exit_price?: number;
  current_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_percent?: number;
  notes?: string;
  deleted_at?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Create position request payload
 */
export interface CreatePositionRequest {
  portfolio_id: string;
  symbol: string;
  quantity: number;
  avg_cost: number;
  position_type: PositionType;
  investment_class: InvestmentClass;
  entry_date?: string;
  notes?: string;
}

/**
 * Update position request payload
 */
export interface UpdatePositionRequest {
  quantity?: number;
  avg_cost?: number;
  position_type?: PositionType;
  investment_class?: InvestmentClass;
  notes?: string;
  entry_date?: string;
  exit_date?: string;
  exit_price?: number;
  entry_price?: number;
  close_quantity?: number;
}

/**
 * Bulk create position data
 */
export interface BulkPositionData {
  symbol: string;
  quantity: number;
  avg_cost: number;
  position_type: PositionType;
  investment_class: InvestmentClass;
  entry_date?: string;
  notes?: string;
}

/**
 * Symbol validation response
 */
export interface SymbolValidationResponse {
  is_valid: boolean;
  message: string;
  symbol: string;
}

/**
 * Duplicate check response
 */
export interface DuplicateCheckResponse {
  has_duplicates: boolean;
  existing_positions: Position[];
  total_count: number;
  message: string;
}

/**
 * Soft delete response
 */
export interface SoftDeleteResponse {
  success: boolean;
  position_id: string;
  symbol: string;
  deleted_at: string;
  message: string;
}

/**
 * Bulk delete response
 */
export interface BulkDeleteResponse {
  success: boolean;
  count: number;
  positions: string[];
  message: string;
}

/**
 * Hard delete response
 */
export interface HardDeleteResponse {
  success: boolean;
  position_id: string;
  symbol: string;
  permanently_deleted: boolean;
  message: string;
}

// ===== Position Management Service Class =====

export class PositionManagementService {
  /**
   * Get authentication headers for API requests
   */
  private getAuthHeaders(): Record<string, string> {
    const token = authManager.getAccessToken();
    if (!token) {
      throw new Error('Not authenticated - please login first');
    }

    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  // ===== CORE CRUD OPERATIONS =====

  /**
   * Create a new position
   * Backend: POST /api/v1/positions
   */
  async createPosition(data: CreatePositionRequest): Promise<Position> {
    const response = await apiClient.post<Position>(
      '/api/v1/positions',
      data,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  /**
   * Get a single position by ID
   * Backend: GET /api/v1/positions/{id}
   */
  async getPosition(positionId: string): Promise<Position> {
    const response = await apiClient.get<Position>(
      `/api/v1/positions/${positionId}`,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  /**
   * Update an existing position
   * Backend: PUT /api/v1/positions/{id}
   */
  async updatePosition(
    positionId: string,
    data: UpdatePositionRequest
  ): Promise<Position> {
    const response = await apiClient.put<Position>(
      `/api/v1/positions/${positionId}`,
      data,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  /**
   * Soft delete a position (sets deleted_at timestamp)
   * Backend: DELETE /api/v1/positions/{id}
   */
  async softDeletePosition(positionId: string): Promise<SoftDeleteResponse> {
    const response = await apiClient.delete<SoftDeleteResponse>(
      `/api/v1/positions/${positionId}`,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  /**
   * Hard delete a position (permanent removal - Reverse Addition)
   * Only works for positions < 5 minutes old with no snapshots
   * Backend: DELETE /api/v1/positions/{id}/hard
   */
  async hardDeletePosition(positionId: string): Promise<HardDeleteResponse> {
    const response = await apiClient.delete<HardDeleteResponse>(
      `/api/v1/positions/${positionId}/hard`,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  // ===== SMART FEATURES =====

  /**
   * Validate if a symbol exists in market data
   * Backend: GET /api/v1/positions/validate-symbol/{symbol}
   */
  async validateSymbol(symbol: string): Promise<SymbolValidationResponse> {
    const response = await apiClient.get<SymbolValidationResponse>(
      `/api/v1/positions/validate-symbol/${symbol.toUpperCase()}`,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  /**
   * Check for duplicate positions in a portfolio
   * Backend: GET /api/v1/positions/check-duplicate
   */
  async checkDuplicatePositions(
    portfolioId: string,
    symbol: string,
    positionType?: PositionType
  ): Promise<DuplicateCheckResponse> {
    const params = new URLSearchParams({
      portfolio_id: portfolioId,
      symbol: symbol.toUpperCase(),
    });

    if (positionType) {
      params.append('position_type', positionType);
    }

    const response = await apiClient.get<DuplicateCheckResponse>(
      `/api/v1/positions/check-duplicate?${params.toString()}`,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  // ===== BULK OPERATIONS =====

  /**
   * Bulk create multiple positions
   * Backend: POST /api/v1/positions/bulk
   */
  async bulkCreatePositions(
    portfolioId: string,
    positions: BulkPositionData[]
  ): Promise<{ positions: Position[]; count: number; message: string }> {
    const response = await apiClient.post<{
      positions: Position[];
      count: number;
      message: string;
    }>(
      '/api/v1/positions/bulk',
      {
        portfolio_id: portfolioId,
        positions,
      },
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  /**
   * Bulk soft delete multiple positions
   * Backend: DELETE /api/v1/positions/bulk
   */
  async bulkDeletePositions(
    positionIds: string[]
  ): Promise<BulkDeleteResponse> {
    const response = await apiClient.delete<BulkDeleteResponse>(
      '/api/v1/positions/bulk',
      { position_ids: positionIds },
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    );
    return response;
  }

  // ===== CONVENIENCE METHODS =====

  /**
   * Close a position (sets exit_date and exit_price)
   * This is a convenience method that uses the update endpoint
   */
  async closePosition(
    positionId: string,
    exitPrice: number,
    exitDate?: string
  ): Promise<Position> {
    return this.updatePosition(positionId, {
      exit_price: exitPrice,
      exit_date: exitDate || new Date().toISOString().split('T')[0],
    });
  }

  /**
   * Update position notes only
   * This is a convenience method that uses the update endpoint
   */
  async updateNotes(positionId: string, notes: string): Promise<Position> {
    return this.updatePosition(positionId, { notes });
  }

  /**
   * Update position quantity and average cost
   * Useful for tax lot averaging scenarios
   */
  async updateQuantityAndCost(
    positionId: string,
    quantity: number,
    avgCost: number
  ): Promise<Position> {
    return this.updatePosition(positionId, {
      quantity,
      avg_cost: avgCost,
    });
  }

  /**
   * Check if a symbol is valid before creating a position
   * Returns true if valid, throws error if invalid
   */
  async ensureSymbolValid(symbol: string): Promise<boolean> {
    const validation = await this.validateSymbol(symbol);
    if (!validation.is_valid) {
      throw new Error(validation.message);
    }
    return true;
  }

  /**
   * Create position with duplicate check
   * Throws error if duplicate exists (unless allow_duplicate is true)
   */
  async createPositionWithDuplicateCheck(
    data: CreatePositionRequest,
    allowDuplicate = false
  ): Promise<Position> {
    // Check for duplicates
    const duplicateCheck = await this.checkDuplicatePositions(
      data.portfolio_id,
      data.symbol,
      data.position_type
    );

    if (duplicateCheck.has_duplicates && !allowDuplicate) {
      throw new Error(
        `Duplicate position found: ${duplicateCheck.total_count} existing ${data.symbol} position(s). ` +
        `Use allowDuplicate=true to create anyway.`
      );
    }

    // Create position
    return this.createPosition(data);
  }
}

// Export singleton instance
export default new PositionManagementService();
