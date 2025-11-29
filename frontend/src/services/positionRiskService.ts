/**
 * Position Risk Metrics Service
 *
 * Centralizes all position-level risk metrics API calls:
 * - Company profile data (beta, sector, industry)
 * - Factor exposures (Growth, Momentum, Size, etc.)
 * - Volatility metrics
 *
 * All data sourced from backend tables and APIs
 */

import { apiClient } from './apiClient'
import { API_ENDPOINTS } from '@/config/api'

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {}
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Types
// Factor names must match backend FactorDefinition names in seed_factors.py
export interface PositionFactorExposures {
  'Market Beta (90D)'?: number  // 90-day OLS regression beta vs S&P 500
  'Provider Beta (1Y)'?: number // 1-year market beta from data providers
  'IR Beta'?: number            // Interest rate sensitivity vs TLT
  'Size'?: number
  'Value'?: number
  'Momentum'?: number
  'Quality'?: number
  'Low Volatility'?: number
  'Growth'?: number
}

export interface PositionRiskMetrics {
  symbol: string
  position_id: string

  // From company_profiles table
  beta?: number
  sector?: string
  industry?: string
  market_cap?: number

  // From position_factor_exposures table
  factor_exposures?: PositionFactorExposures

  // Calculated/derived
  volatility_30d?: number
}

export interface PositionFactorExposuresResponse {
  available: boolean
  portfolio_id: string
  calculation_date: string
  total: number
  limit: number
  offset: number
  positions: Array<{
    position_id: string
    symbol: string
    exposures: PositionFactorExposures
  }>
}

/**
 * Get complete risk metrics for a position
 */
export async function getPositionRiskMetrics(
  portfolioId: string,
  positionId: string,
  symbol: string
): Promise<PositionRiskMetrics> {
  console.log('🔍 Position Risk Service: Fetching metrics', { portfolioId, positionId, symbol })

  const metrics: PositionRiskMetrics = {
    symbol,
    position_id: positionId
  }

  try {
    // Fetch position factor exposures
    const factorEndpoint = API_ENDPOINTS.ANALYTICS.POSITIONS_FACTOR_EXPOSURES(portfolioId)
    const factorResponse = await apiClient.get<PositionFactorExposuresResponse>(
      `${factorEndpoint}?symbols=${symbol}`,
      {
        headers: { ...getAuthHeader() },
        timeout: 10000
      }
    )

    console.log('🔍 Position Risk Service: Factor exposures response', factorResponse)

    if (factorResponse.available && factorResponse.positions.length > 0) {
      const positionData = factorResponse.positions.find(p => p.position_id === positionId || p.symbol === symbol)
      if (positionData) {
        metrics.factor_exposures = positionData.exposures
        // Market Beta (90D) is the calculated beta from factor exposures
        metrics.beta = positionData.exposures['Market Beta (90D)']
      }
    }
  } catch (error) {
    console.warn('⚠️ Position Risk Service: Factor exposures unavailable', error)
  }

  // TODO: Add company profile fetch for sector, industry if not in position data
  // TODO: Add volatility calculation/fetch

  console.log('✅ Position Risk Service: Complete metrics', metrics)
  return metrics
}

/**
 * Get factor exposures for multiple positions
 */
export async function getBatchPositionFactorExposures(
  portfolioId: string,
  symbols: string[]
): Promise<Map<string, PositionFactorExposures>> {
  const endpoint = API_ENDPOINTS.ANALYTICS.POSITIONS_FACTOR_EXPOSURES(portfolioId)
  const symbolsParam = symbols.join(',')

  try {
    const response = await apiClient.get<PositionFactorExposuresResponse>(
      `${endpoint}?symbols=${symbolsParam}`,
      {
        headers: { ...getAuthHeader() },
        timeout: 15000
      }
    )

    const exposuresMap = new Map<string, PositionFactorExposures>()
    if (response.available) {
      response.positions.forEach(pos => {
        exposuresMap.set(pos.symbol, pos.exposures)
      })
    }

    return exposuresMap
  } catch (error) {
    console.error('Error fetching batch factor exposures:', error)
    return new Map()
  }
}

export const positionRiskService = {
  getPositionRiskMetrics,
  getBatchPositionFactorExposures
}

export default positionRiskService
