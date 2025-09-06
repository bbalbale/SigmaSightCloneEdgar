/**
 * Portfolio Service - Fetches real portfolio data from backend
 */

import { portfolioResolver } from './portfolioResolver'
import { authManager } from './authManager'
import { requestManager } from './requestManager'
import { positionApiService } from './positionApiService'

export type PortfolioType = 'individual' | 'high-net-worth' | 'hedge-fund'

interface PortfolioData {
  portfolio: {
    id: string
    name: string
    total_value: number
    cash_balance: number
    position_count: number
  }
  positions_summary: {
    long_count: number
    short_count: number
    option_count: number
    total_market_value: number
  }
  holdings: Array<{
    id: string
    symbol: string
    quantity: number
    position_type: string
    market_value: number
    last_price: number
  }>
}

/**
 * Load portfolio data for a specific portfolio type
 * Now with centralized auth and retry logic
 * Phase 3: Use API for positions when USE_API_POSITIONS is enabled
 */
export async function loadPortfolioData(
  portfolioType: PortfolioType, 
  abortSignal?: AbortSignal,
  useApiPositions: boolean = false
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
      // Use the retry ID
      const portfolioIdFinal = retryId
      
      // Fetch portfolio data with retry logic and data-level deduplication
      const data: PortfolioData = await requestManager.authenticatedFetchJson(
        `/api/proxy/api/v1/data/portfolio/${portfolioIdFinal}/complete`,
        refreshedToken,
        {
          signal: abortSignal,
          maxRetries: 3,
          timeout: 15000,
          dedupe: true
        }
      )
      
      // Transform to UI-friendly format
      return {
        exposures: calculateExposures(data),
        positions: transformPositions(data.holdings),
        portfolioInfo: data.portfolio
      }
    }
    
    // Fetch portfolio data with retry logic
    const response = await requestManager.authenticatedFetch(
      `/api/proxy/api/v1/data/portfolio/${portfolioId}/complete`,
      token,
      {
        signal: abortSignal,
        maxRetries: 3,
        timeout: 15000,
        dedupe: true
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to load portfolio: ${response.status}`)
    }

    const data: PortfolioData = await response.json()
    
    // Phase 3: Try to use API positions if enabled
    let positionsData = transformPositions(data.holdings)
    let dataSource: 'live' | 'cached' = 'cached'
    
    if (useApiPositions) {
      try {
        console.log('📊 Phase 3: Attempting to fetch positions from API...')
        const apiStartTime = performance.now()
        
        const apiResponse = await positionApiService.fetchPositionsFromApi(
          portfolioId,
          portfolioType,
          abortSignal
        )
        
        if (apiResponse && apiResponse.positions.length > 0) {
          // Transform API positions to UI format
          positionsData = apiResponse.positions.map(pos => ({
            symbol: pos.symbol,
            quantity: pos.quantity,
            price: pos.current_price,
            marketValue: pos.market_value,
            pnl: pos.unrealized_pnl, // Will be 0 from API
            positive: pos.unrealized_pnl >= 0,
            type: pos.position_type
          }))
          dataSource = 'live'
          console.log(`📊 Phase 3: Successfully using API positions (${performance.now() - apiStartTime}ms)`)
        } else {
          console.log('📊 Phase 3: API returned no positions, using fallback')
        }
      } catch (apiError) {
        console.error('📊 Phase 3: Failed to fetch API positions, using fallback:', apiError)
        // Keep using transformed data from complete endpoint
      }
    }
    
    // Transform to UI-friendly format
    return {
      exposures: calculateExposures(data),
      positions: positionsData,
      portfolioInfo: data.portfolio,
      positionsDataSource: dataSource
    }
  } catch (error: any) {
    // Don't log abort errors
    if (error.name !== 'AbortError') {
      console.error(`Failed to load portfolio data for ${portfolioType}:`, error)
    }
    throw error
  }
}

/**
 * Calculate exposure metrics from portfolio data
 */
function calculateExposures(data: PortfolioData) {
  const totalValue = data.portfolio.total_value
  const longValue = data.positions_summary.total_market_value
  const shortValue = 0 // No short positions in demo data
  const grossExposure = longValue + shortValue
  const netExposure = longValue - shortValue
  
  return [
    {
      title: 'Long Exposure',
      value: formatCurrency(longValue),
      subValue: `${((longValue / totalValue) * 100).toFixed(1)}%`,
      description: 'Notional exposure',
      positive: true
    },
    {
      title: 'Short Exposure',
      value: shortValue > 0 ? `(${formatCurrency(shortValue)})` : '$0',
      subValue: `${((shortValue / totalValue) * 100).toFixed(1)}%`,
      description: 'Notional exposure',
      positive: false
    },
    {
      title: 'Gross Exposure',
      value: formatCurrency(grossExposure),
      subValue: `${((grossExposure / totalValue) * 100).toFixed(1)}%`,
      description: 'Notional total',
      positive: true
    },
    {
      title: 'Net Exposure',
      value: formatCurrency(netExposure),
      subValue: `${((netExposure / totalValue) * 100).toFixed(1)}%`,
      description: 'Notional net',
      positive: true
    },
    {
      title: 'Cash Balance',
      value: formatCurrency(data.portfolio.cash_balance),
      subValue: `${((data.portfolio.cash_balance / totalValue) * 100).toFixed(1)}%`,
      description: `Total Value: ${formatCurrency(totalValue)}`,
      positive: true
    },
    {
      title: 'Total P&L',
      value: 'Data Not Available',
      subValue: 'N/A',
      description: 'P&L data not available in this endpoint',
      positive: true
    }
  ]
}

/**
 * Transform holdings to position format for UI
 */
function transformPositions(holdings: PortfolioData['holdings']) {
  return holdings.map(holding => ({
    symbol: holding.symbol,
    quantity: holding.quantity,
    price: holding.last_price,
    marketValue: holding.market_value,
    pnl: 0, // P&L data not available in this endpoint
    positive: true,
    type: holding.position_type
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