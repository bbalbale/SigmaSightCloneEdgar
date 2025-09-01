/**
 * Portfolio Service - Fetches real portfolio data from backend
 */

// Map portfolio types to backend portfolio IDs
const PORTFOLIO_ID_MAP = {
  'individual': '52110fe1-ca52-42ff-abaa-c0c90e8e21be',
  'high-net-worth': '7ec9dab7-b709-4a3a-b7b6-2399e53ac3eb',
  'hedge-fund': '1341a9f2-5ef1-4acb-a480-2dca21a7d806'
}

// Demo user credentials for authentication
const DEMO_CREDENTIALS = {
  'individual': { email: 'demo_individual@sigmasight.com', password: 'demo12345' },
  'high-net-worth': { email: 'demo_hnw@sigmasight.com', password: 'demo12345' },
  'hedge-fund': { email: 'demo_hedgefundstyle@sigmasight.com', password: 'demo12345' }
}

export type PortfolioType = 'individual' | 'high-net-worth' | 'hedge-fund'

interface AuthToken {
  access_token: string
  token_type: string
  expires_in: number
}

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
 * Authenticate with the backend to get an access token
 */
async function authenticate(portfolioType: PortfolioType): Promise<string> {
  const credentials = DEMO_CREDENTIALS[portfolioType]
  
  const response = await fetch('/api/proxy/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials)
  })

  if (!response.ok) {
    throw new Error(`Authentication failed: ${response.status}`)
  }

  const data: AuthToken = await response.json()
  return data.access_token
}

/**
 * Load portfolio data for a specific portfolio type
 * For now, only 'high-net-worth' returns real data
 */
export async function loadPortfolioData(portfolioType: PortfolioType) {
  // Only fetch real data for high-net-worth
  if (portfolioType !== 'high-net-worth') {
    return null // Will use dummy data in the UI
  }

  try {
    // Get authentication token
    const token = await authenticate(portfolioType)
    
    // Get portfolio ID
    const portfolioId = PORTFOLIO_ID_MAP[portfolioType]
    
    // Fetch portfolio data
    const response = await fetch(
      `/api/proxy/api/v1/data/portfolio/${portfolioId}/complete`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to load portfolio: ${response.status}`)
    }

    const data: PortfolioData = await response.json()
    
    // Transform to UI-friendly format
    return {
      exposures: calculateExposures(data),
      positions: transformPositions(data.holdings),
      portfolioInfo: data.portfolio
    }
  } catch (error) {
    console.error(`Failed to load portfolio data for ${portfolioType}:`, error)
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