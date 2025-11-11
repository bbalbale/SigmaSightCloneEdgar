import { apiClient } from './apiClient'
import { authManager } from './authManager'
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api'
import type { TargetPrice } from '@/lib/types'

export interface PortfolioTargetPriceSummary {
  portfolio_id: string
  portfolio_name: string
  total_positions: number
  positions_with_targets: number
  coverage_percentage: number | null
  weighted_expected_return_eoy: number | null
  weighted_expected_return_next_year: number | null
  weighted_downside_return: number | null
  expected_sharpe_ratio: number | null
  expected_sortino_ratio: number | null
  target_prices?: TargetPrice[]
  last_updated: string | null
}

/**
 * Target Price API Service - User-defined price targets
 *
 * This service handles CRUD operations for user-entered target prices.
 * Target prices include EOY and next year targets for each position.
 *
 * Architecture:
 * - Each target price record contains both target_price_eoy AND target_price_next_year
 * - Backend auto-calculates expected returns from current price
 * - Smart upsert: tries to update existing, falls back to create if not found
 *
 * Related Files:
 * - Backend: backend/app/api/v1/target_prices.py
 * - Service: src/services/positionResearchService.ts (reads targets)
 * - Component: src/components/positions/ResearchPositionCard.tsx (displays/edits)
 */
export class TargetPriceApi {
  private getAuthHeaders() {
    const token = authManager.getAccessToken()
    if (!token) {
      throw new Error('Not authenticated')
    }

    return {
      Authorization: `Bearer ${token}`,
    }
  }

  /**
   * List all target prices for a portfolio
   * @param portfolioId - Portfolio UUID
   * @param symbol - Optional filter by symbol
   * @param positionType - Optional filter by position type
   */
  async list(portfolioId: string, symbol?: string, positionType?: string): Promise<TargetPrice[]> {
    let url = API_ENDPOINTS.TARGET_PRICES.LIST(portfolioId)

    const params = new URLSearchParams()
    if (symbol) params.append('symbol', symbol)
    if (positionType) params.append('position_type', positionType)

    if (params.toString()) {
      url += `?${params.toString()}`
    }

    const resp = await apiClient.get(url, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: this.getAuthHeaders(),
    })
    return (Array.isArray(resp) ? resp : []) as TargetPrice[]
  }

  /**
   * Get a specific target price by symbol and position type
   * @param portfolioId - Portfolio UUID
   * @param symbol - Symbol to lookup
   * @param positionType - Position type (LONG, SHORT, etc.)
   */
  async get(portfolioId: string, symbol: string, positionType: string): Promise<TargetPrice | null> {
    const targets = await this.list(portfolioId, symbol, positionType)
    return targets.length > 0 ? targets[0] : null
  }

  /**
   * Create a new target price
   * @param portfolioId - Portfolio UUID
   * @param data - Target price data
   */
  async create(portfolioId: string, data: {
    symbol: string
    position_type: string
    target_price_eoy?: number
    target_price_next_year?: number
    downside_target_price?: number
    current_price: number
    position_id?: string
  }): Promise<TargetPrice> {
    const resp = await apiClient.post(
      API_ENDPOINTS.TARGET_PRICES.CREATE(portfolioId),
      data,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    )
    return resp as TargetPrice
  }

  /**
   * Update an existing target price
   * @param targetPriceId - Target price UUID
   * @param data - Fields to update
   */
  async update(targetPriceId: string, data: {
    target_price_eoy?: number
    target_price_next_year?: number
    downside_target_price?: number
    current_price?: number
  }): Promise<TargetPrice> {
    const resp = await apiClient.put(
      API_ENDPOINTS.TARGET_PRICES.UPDATE(targetPriceId),
      data,
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    )
    return resp as TargetPrice
  }

  /**
   * Fetch portfolio-level target price summary (weighted returns, coverage, etc.)
   * @param portfolioId - Portfolio UUID
   */
  async summary(portfolioId: string): Promise<PortfolioTargetPriceSummary> {
    const resp = await apiClient.get(
      API_ENDPOINTS.TARGET_PRICES.SUMMARY(portfolioId),
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    )

    if (resp && typeof (resp as any).data !== 'undefined') {
      const summary = (resp as any).data as PortfolioTargetPriceSummary
      console.log('[targetPriceService.summary] API response (data wrapper):', summary)
      return summary
    }

    console.log('[targetPriceService.summary] API response (raw):', resp)
    return resp as PortfolioTargetPriceSummary
  }

  /**
   * Smart upsert - creates if doesn't exist, updates if it does
   * @param portfolioId - Portfolio UUID
   * @param data - Target price data including symbol and position_type for lookup
   */
  async createOrUpdate(portfolioId: string, data: {
    symbol: string
    position_type: string
    target_price_eoy?: number
    target_price_next_year?: number
    downside_target_price?: number
    current_price: number
    position_id?: string
  }): Promise<TargetPrice> {
    // Try to find existing target price
    const existing = await this.get(portfolioId, data.symbol, data.position_type)

    if (existing) {
      // Update existing
      return await this.update(existing.id, {
        target_price_eoy: data.target_price_eoy,
        target_price_next_year: data.target_price_next_year,
        downside_target_price: data.downside_target_price,
        current_price: data.current_price,
      })
    } else {
      // Create new
      return await this.create(portfolioId, data)
    }
  }

  /**
   * Bulk update target prices by symbol
   * @param portfolioId - Portfolio UUID
   * @param updates - Array of updates with symbol, position_type, and target fields
   */
  async bulkUpdate(portfolioId: string, updates: Array<{
    symbol: string
    position_type: string
    target_price_eoy?: number
    target_price_next_year?: number
    downside_target_price?: number
    current_price?: number
  }>): Promise<{ updated: number; errors: string[] }> {
    const resp = await apiClient.put(
      API_ENDPOINTS.TARGET_PRICES.BULK_UPDATE(portfolioId),
      { updates },
      {
        ...REQUEST_CONFIGS.STANDARD,
        headers: this.getAuthHeaders(),
      }
    )
    return resp as { updated: number; errors: string[] }
  }
}

export default new TargetPriceApi()
