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

    const results = await fetchPortfolioDataFromApis(portfolioId, token, abortSignal)
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
  abortSignal?: AbortSignal
) {
  const [overviewResult, positionsResult, factorExposuresResult] = await Promise.allSettled([
    analyticsApi.getOverview(portfolioId),
    apiClient.get<{ positions: PositionDetail[] }>(
      `/api/v1/data/positions/details?portfolio_id=${portfolioId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortSignal
      }
    ),
    apiClient.get<any>(
      `/api/v1/analytics/portfolio/${portfolioId}/factor-exposures`,
      {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortSignal
      }
    ).then(response => {
      console.log('Factor exposures API response:', response)
      return response
    })
  ])

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

  let factorExposures: FactorExposure[] | null = null
  if (factorExposuresResult.status === 'fulfilled') {
    if (factorExposuresResult.value?.data?.available && factorExposuresResult.value?.data?.factors) {
      factorExposures = factorExposuresResult.value.data.factors
    } else if (factorExposuresResult.value?.available && factorExposuresResult.value?.factors) {
      factorExposures = factorExposuresResult.value.factors
    } else {
      console.log('Factor exposures not available in response')
    }
  } else if (factorExposuresResult.status === 'rejected') {
    console.error('Failed to fetch factor exposures:', factorExposuresResult.reason)
  }

  return {
    exposures,
    positions,
    portfolioInfo,
    factorExposures,
    errors: {
      overview: overviewResult.status === 'rejected' ? overviewResult.reason : null,
      positions: positionsResult.status === 'rejected' ? positionsResult.reason : null,
      factorExposures: factorExposuresResult.status === 'rejected' ? factorExposuresResult.reason : null
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
