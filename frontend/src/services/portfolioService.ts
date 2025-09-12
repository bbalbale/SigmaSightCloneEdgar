/**
 * Portfolio Service - Fetches real portfolio data from backend
 */

import { portfolioResolver } from './portfolioResolver'
import { authManager } from './authManager'
import { requestManager } from './requestManager'
import { positionApiService } from './positionApiService'
import { analyticsApi } from './analyticsApi'
import { apiClient } from './apiClient'

export type PortfolioType = 'individual' | 'high-net-worth' | 'hedge-fund'

interface PositionDetail {
  id: string
  symbol: string
  quantity: number
  position_type: string
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  realized_pnl: number
}

/**
 * Load portfolio data for a specific portfolio type
 * Uses individual APIs instead of /complete endpoint
 */
export async function loadPortfolioData(
  portfolioType: PortfolioType, 
  abortSignal?: AbortSignal
) {
  // Fetch real data for all portfolio types
  if (!portfolioType) {
    return null // No portfolio type specified
  }

  try {
    // Get authentication token from centralized manager
    const token = await authManager.getToken(portfolioType)
    
    // Clear portfolio resolver cache to ensure fresh resolution
    portfolioResolver.clearCache()
    
    // Update token and email in localStorage for portfolio resolver
    localStorage.setItem('access_token', token)
    
    // Store the email for portfolio resolver to use
    const DEMO_CREDENTIALS = {
      'individual': { email: 'demo_individual@sigmasight.com', password: 'demo12345' },
      'high-net-worth': { email: 'demo_hnw@sigmasight.com', password: 'demo12345' },
      'hedge-fund': { email: 'demo_hedgefundstyle@sigmasight.com', password: 'demo12345' }
    }
    const credentials = DEMO_CREDENTIALS[portfolioType]
    if (credentials) {
      localStorage.setItem('user_email', credentials.email)
    }
    
    // Dynamically resolve portfolio ID with the fresh token
    const portfolioId = await portfolioResolver.getPortfolioIdByType(portfolioType)
    if (!portfolioId) {
      // Try refreshing the token and retrying once
      const refreshedToken = await authManager.refreshToken(portfolioType)
      localStorage.setItem('access_token', refreshedToken)
      const retryId = await portfolioResolver.getPortfolioIdByType(portfolioType)
      
      if (!retryId) {
        throw new Error(`Could not resolve portfolio ID for type: ${portfolioType}`)
      }
      // Use the retry ID for subsequent API calls
      const portfolioIdFinal = retryId
      
      // Fetch data from individual APIs in parallel
      const results = await fetchPortfolioDataFromApis(portfolioIdFinal, refreshedToken, abortSignal)
      return results
    }
    
    // Fetch data from individual APIs in parallel
    const results = await fetchPortfolioDataFromApis(portfolioId, token, abortSignal)
    return results
  } catch (error: any) {
    // Don't log abort errors
    if (error.name !== 'AbortError') {
      console.error(`Failed to load portfolio data for ${portfolioType}:`, error)
    }
    throw error
  }
}

/**
 * Fetch portfolio data from individual APIs
 */
async function fetchPortfolioDataFromApis(
  portfolioId: string,
  token: string,
  abortSignal?: AbortSignal
) {
  // Make parallel API calls using Promise.allSettled to handle partial failures
  const [overviewResult, positionsResult] = await Promise.allSettled([
    // Fetch portfolio overview with exposures
    analyticsApi.getOverview(portfolioId),
    // Fetch positions with details
    apiClient.get<{ positions: PositionDetail[] }>(
      `/api/v1/data/positions/details?portfolio_id=${portfolioId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortSignal
      }
    )
  ])

  // Handle overview API result
  let exposures = []
  let portfolioInfo = null
  if (overviewResult.status === 'fulfilled') {
    const overview = overviewResult.value.data
    exposures = calculateExposuresFromOverview(overview)
    portfolioInfo = {
      id: overview.portfolio_id,
      name: `Portfolio ${portfolioId.slice(0, 8)}`, // Use portfolio ID as fallback name
      total_value: overview.total_value,
      cash_balance: overview.cash_balance,
      position_count: overview.position_count?.total_positions || 0
    }
  } else {
    console.error('Failed to fetch portfolio overview:', overviewResult.reason)
    // Re-throw the error since we need overview data
    throw new Error(`Portfolio overview unavailable: ${overviewResult.reason}`)
  }

  // Handle positions API result
  let positions = []
  if (positionsResult.status === 'fulfilled') {
    positions = transformPositionDetails(positionsResult.value.positions)
  } else {
    console.error('Failed to fetch positions:', positionsResult.reason)
    // Return empty positions array but don't fail entirely
    positions = []
  }

  return {
    exposures,
    positions,
    portfolioInfo,
    errors: {
      overview: overviewResult.status === 'rejected' ? overviewResult.reason : null,
      positions: positionsResult.status === 'rejected' ? positionsResult.reason : null
    }
  }
}

/**
 * Calculate exposure metrics from overview API response
 */
function calculateExposuresFromOverview(overview: any) {
  const totalValue = overview.total_value || 0
  const exposures = overview.exposures || {}
  const longValue = exposures.long_exposure || 0
  const shortValue = Math.abs(exposures.short_exposure || 0) // Make positive for display
  const grossExposure = exposures.gross_exposure || (longValue + shortValue)
  const netExposure = exposures.net_exposure || (longValue - shortValue)
  const cashBalance = overview.cash_balance || 0
  const pnl = overview.pnl || {}
  const totalPnl = pnl.unrealized_pnl || 0
  
  return [
    {
      title: 'Long Exposure',
      value: formatCurrency(longValue),
      subValue: totalValue > 0 ? `${((longValue / totalValue) * 100).toFixed(1)}%` : '0%',
      description: 'Notional exposure',
      positive: true
    },
    {
      title: 'Short Exposure',
      value: shortValue > 0 ? `(${formatCurrency(shortValue)})` : '$0',
      subValue: totalValue > 0 ? `${((shortValue / totalValue) * 100).toFixed(1)}%` : '0%',
      description: 'Notional exposure',
      positive: false
    },
    {
      title: 'Gross Exposure',
      value: formatCurrency(grossExposure),
      subValue: totalValue > 0 ? `${((grossExposure / totalValue) * 100).toFixed(1)}%` : '0%',
      description: 'Notional total',
      positive: true
    },
    {
      title: 'Net Exposure',
      value: formatCurrency(netExposure),
      subValue: totalValue > 0 ? `${((netExposure / totalValue) * 100).toFixed(1)}%` : '0%',
      description: 'Notional net',
      positive: true
    },
    {
      title: 'Cash Balance',
      value: formatCurrency(cashBalance),
      subValue: totalValue > 0 ? `${((cashBalance / totalValue) * 100).toFixed(1)}%` : '0%',
      description: `Total Value: ${formatCurrency(totalValue)}`,
      positive: true
    },
    {
      title: 'Total P&L',
      value: formatCurrency(totalPnl),
      subValue: totalPnl !== 0 ? (totalPnl > 0 ? '+' : '') + totalPnl.toFixed(2) : 'N/A',
      description: 'Unrealized P&L',
      positive: totalPnl >= 0
    }
  ]
}

/**
 * Transform position details from API to UI format
 */
function transformPositionDetails(positions: PositionDetail[]) {
  return positions.map(pos => ({
    symbol: pos.symbol,
    quantity: pos.quantity,
    price: pos.current_price,
    marketValue: pos.market_value,
    pnl: pos.unrealized_pnl,
    positive: pos.unrealized_pnl >= 0,
    type: pos.position_type
  }))
}

/**
 * Format currency values
 */
function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(0)}`
}