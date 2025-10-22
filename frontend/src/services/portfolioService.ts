/**
 * Portfolio Service - Fetches real portfolio data from backend
 */

import { portfolioResolver } from './portfolioResolver'
import { authManager } from './authManager'
import { analyticsApi } from './analyticsApi'
import { apiClient } from './apiClient'
import type { FactorExposure } from '../types/analytics'

interface PositionDetail {
  id: string
  symbol: string
  company_name?: string
  sector?: string  // NEW: Company sector classification
  industry?: string  // NEW: Company industry classification
  quantity: number
  position_type: string
  investment_class?: string  // PUBLIC, OPTIONS, PRIVATE
  investment_subtype?: string
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  realized_pnl: number
  // Option-specific fields
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
}

type LoadOptions = {
  portfolioId?: string | null
  forceRefresh?: boolean
  skipFactorExposures?: boolean
}

/**
 * Load portfolio data for the authenticated user
 * Uses individual APIs instead of /complete endpoint
 */
export async function loadPortfolioData(
  abortSignal?: AbortSignal,
  options: LoadOptions = {}
) {
  try {
    const token = authManager.getAccessToken()
    if (!token) {
      throw new Error('Authentication token unavailable')
    }

    let portfolioId = options.portfolioId ?? authManager.getPortfolioId()

    if (!portfolioId || options.forceRefresh) {
      if (options.forceRefresh) {
        portfolioResolver.clearCache()
      }
      portfolioId = await portfolioResolver.getUserPortfolioId(options.forceRefresh)
    }

    if (!portfolioId) {
      throw new Error('Could not resolve portfolio ID for current user')
    }

    authManager.setPortfolioId(portfolioId)

    const results = await fetchPortfolioDataFromApis(portfolioId, token, abortSignal, options.skipFactorExposures)
    return {
      ...results,
      portfolioId
    }
  } catch (error: any) {
    if (error?.name !== 'AbortError') {
      console.error('Failed to load portfolio data:', error)
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
  abortSignal?: AbortSignal,
  skipFactorExposures?: boolean
) {
  // Build the promises array conditionally based on skipFactorExposures
  const promises: Promise<any>[] = [
    analyticsApi.getOverview(portfolioId),
    apiClient.get<{ positions: PositionDetail[] }>(
      `/api/v1/data/positions/details?portfolio_id=${portfolioId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortSignal
      }
    )
  ]

  // Only add factor exposures and market beta calls if not skipped
  if (!skipFactorExposures) {
    promises.push(
      // Factor exposures can be slow - increase timeout and reduce retries
      apiClient.get<any>(
        `/api/v1/analytics/portfolio/${portfolioId}/factor-exposures`,
        {
          headers: { Authorization: `Bearer ${token}` },
          signal: abortSignal,
          timeout: 60000,  // Increased to 60 seconds (from default 30s)
          retries: 1       // Reduced to 1 retry (from default 2) for faster failure
        }
      ).then(response => {
        console.log('Factor exposures API response:', response)
        return response
      })
    )
  }

  const results = await Promise.allSettled(promises)
  const [overviewResult, positionsResult, factorExposuresResult] = results

  let portfolioInfo: { name: string } | null = null
  let exposures = [] as any[]

  if (overviewResult.status === 'fulfilled') {
    const overviewResponse = overviewResult.value.data
    exposures = calculateExposuresFromOverview(overviewResponse)
    portfolioInfo = {
      name: 'Portfolio'
    }
  } else {
    console.error('Failed to fetch portfolio overview:', overviewResult.reason)
  }

  let positions: any[] = []
  if (positionsResult.status === 'fulfilled') {
    const positionData = positionsResult.value
    if (positionData?.positions) {
      positions = transformPositionDetails(positionData.positions)
    }
  } else {
    console.error('Failed to fetch portfolio positions:', positionsResult.reason)
  }

  // Extract equity balance from overview for components that need it
  let equityBalance = 0
  if (overviewResult.status === 'fulfilled') {
    equityBalance = overviewResult.value.data?.equity_balance || 0
  }

  let factorExposures: FactorExposure[] | null = null
  // Only process factor exposures if they were fetched (not skipped)
  if (factorExposuresResult) {
    if (factorExposuresResult.status === 'fulfilled') {
      if (factorExposuresResult.value?.data?.available && factorExposuresResult.value?.data?.factors) {
        factorExposures = factorExposuresResult.value.data.factors
        console.log('✅ Factor exposures loaded successfully:', factorExposures?.length || 0, 'factors')
      } else if (factorExposuresResult.value?.available && factorExposuresResult.value?.factors) {
        factorExposures = factorExposuresResult.value.factors
        console.log('✅ Factor exposures loaded successfully:', factorExposures?.length || 0, 'factors')
      } else {
        console.log('⚠️ Factor exposures not available in response (may not be calculated yet)')
      }
    } else if (factorExposuresResult.status === 'rejected') {
      console.error('❌ Failed to fetch factor exposures:', factorExposuresResult.reason)
      // Check if it's a timeout error
      if (factorExposuresResult.reason?.name === 'TimeoutError') {
        console.error('💡 Suggestion: Factor exposures endpoint exceeded 60s timeout. Backend may need optimization.')
      }
    }
  } else if (skipFactorExposures) {
    console.log('⏭️ Factor exposures skipped per request')
  }

  return {
    exposures,
    positions,
    portfolioInfo,
    factorExposures,
    equityBalance,
    errors: {
      overview: overviewResult.status === 'rejected' ? overviewResult.reason : null,
      positions: positionsResult.status === 'rejected' ? positionsResult.reason : null,
      factorExposures: factorExposuresResult && factorExposuresResult.status === 'rejected' ? factorExposuresResult.reason : null
    }
  }
}

/**
 * Calculate exposure metrics from overview API response
 */
function calculateExposuresFromOverview(overview: any) {
  const totalValue = overview?.total_value || 0
  const exposures = overview?.exposures || {}
  const longValue = exposures.long_exposure || 0
  const shortValue = Math.abs(exposures.short_exposure || 0)
  const grossExposure = exposures.gross_exposure || (longValue + shortValue)
  const netExposure = exposures.net_exposure || (longValue - shortValue)
  const cashBalance = overview?.cash_balance || 0
  const equityBalance = overview?.equity_balance || 0
  const pnl = overview?.pnl || {}
  const totalPnl = pnl.unrealized_pnl || 0

  return [
    {
      title: 'Equity Balance',
      value: formatCurrency(equityBalance),
      subValue: totalValue > 0 ? `${((equityBalance / totalValue) * 100).toFixed(1)}%` : '0%',
      description: `Total Value: ${formatCurrency(totalValue)}`,
      positive: true
    },
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
    id: pos.id,
    symbol: pos.symbol,
    company_name: pos.company_name,
    sector: pos.sector,  // NEW: Sector classification
    industry: pos.industry,  // NEW: Industry classification
    quantity: pos.quantity,
    price: pos.current_price,
    marketValue: pos.market_value,
    pnl: pos.unrealized_pnl,
    positive: pos.unrealized_pnl >= 0,
    type: pos.position_type,
    investment_class: pos.investment_class || 'PUBLIC',
    investment_subtype: pos.investment_subtype,
    strike_price: pos.strike_price,
    expiration_date: pos.expiration_date,
    underlying_symbol: pos.underlying_symbol,
    tags: (pos as any).tags || [] // Include tags from API response
  }))
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(0)}`
}

/**
 * Portfolio Snapshot Interface
 * Contains portfolio-level target price metrics calculated by backend
 */
export interface PortfolioSnapshot {
  portfolio_id: string
  snapshot_date: string | null
  target_price_return_eoy: number
  target_price_return_next_year: number
  target_price_coverage_pct: number
  target_price_positions_count: number
  target_price_total_positions: number
  target_price_last_updated: string | null
}

/**
 * Fetch latest portfolio snapshot with target price metrics
 * These values are automatically calculated by backend when target prices change
 */
export async function fetchPortfolioSnapshot(portfolioId: string): Promise<PortfolioSnapshot> {
  const token = authManager.getAccessToken()
  if (!token) {
    throw new Error('Authentication token unavailable')
  }

  return await apiClient.get<PortfolioSnapshot>(
    `/api/v1/data/portfolio/${portfolioId}/snapshot`,
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  )
}

/**
 * Restore Sector Tags Response Interface
 */
export interface RestoreSectorTagsResponse {
  success: boolean
  portfolio_id: string
  portfolio_name: string
  positions_tagged: number
  positions_skipped: number
  tags_created: number
  tags_applied: Array<{
    tag_name: string
    position_count: number
  }>
}

/**
 * Restore sector tags for all positions in a portfolio
 *
 * This function:
 * 1. Fetches company profile data for all positions
 * 2. Creates sector tags (if they don't exist) based on company sector
 * 3. Removes existing sector tags and re-applies them
 *
 * Use cases:
 * - User accidentally deleted sector tags
 * - Initial setup of sector tags for existing portfolio
 * - Refresh sector tags after company profile updates
 */
export async function restoreSectorTags(portfolioId: string): Promise<RestoreSectorTagsResponse> {
  const token = authManager.getAccessToken()
  if (!token) {
    throw new Error('Authentication token unavailable')
  }

  console.log(`[restoreSectorTags] Restoring sector tags for portfolio ${portfolioId}`)

  const response = await apiClient.post<RestoreSectorTagsResponse>(
    `/api/v1/data/positions/restore-sector-tags?portfolio_id=${portfolioId}`,
    {},  // Empty body, portfolio_id is in query params
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  )

  console.log(
    `[restoreSectorTags] Success! Tagged ${response.positions_tagged} positions, ` +
    `created ${response.tags_created} new tags, skipped ${response.positions_skipped} positions`
  )

  return response
}
